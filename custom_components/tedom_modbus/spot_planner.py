"""Řízení kogenerace podle spotových cen – plán na den a spínání jednotky."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
import logging

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .planner import (
    blocks_for_temperature,
    day_quarters,
    optimize,
    parse_prices,
    quarter_prices,
    window_mask,
)

_LOGGER = logging.getLogger(__name__)

MODE_OFF, MODE_MANUAL, MODE_TEMP = "off", "manual", "temp"
MODES = {MODE_OFF: "Vypnuto", MODE_MANUAL: "Ručně", MODE_TEMP: "Podle teploty"}
STRATEGY_EXPENSIVE, STRATEGY_CHEAPEST = "expensive", "cheapest"
STRATEGIES = {STRATEGY_EXPENSIVE: "Nejdražší", STRATEGY_CHEAPEST: "Nejlevnější"}

DEFAULT_SETTINGS = {
    "mode": MODE_OFF,
    "strategy": STRATEGY_EXPENSIVE,  # výroba do sítě: běžet, když je elektřina nejdražší
    "runs": 3,            # max. počet startů za den
    "blocks": 3,          # min. délka běhu v 15min blocích (celkem runs × blocks)
    "penalty": 0.0,       # cena jednoho startu (Kč)
    "power_kw": 0.0,      # výkon pro výpočet (0 = jmenovitý výkon z jednotky)
    "window_from": "06:00",
    "window_to": "22:00",
    "no_negative": True,  # při záporné ceně nejet (dodávka do sítě by se platila)
    "temp_cold": 50.0,    # při této teplotě nádrže plný počet bloků
    "temp_warm": 80.0,    # při této teplotě nádrže 0 bloků
    "temp_safety": 90.0,  # pojistka: nad touto teplotou jednotku vypnout
}

# Nastavení, jejichž změna přepočítá plán zítřka
PLAN_KEYS = {"mode", "strategy", "runs", "blocks", "penalty", "power_kw", "window_from",
             "window_to", "no_negative", "temp_cold", "temp_warm"}


def _minutes(value: str) -> int:
    h, m = str(value).split(":")[:2]
    return int(h) * 60 + int(m)


class TedomSpotPlanner:
    """Plánovač pro jednu jednotku (jeden config entry)."""

    def __init__(self, hass: HomeAssistant, entry_id: str, hub, price_entity: str | None,
                 tank_temp_entity: str | None) -> None:
        self.hass = hass
        self.hub = hub
        self.price_entity = price_entity
        self.tank_temp_entity = tank_temp_entity
        self._store = Store(hass, 1, f"tedom_modbus.planner.{entry_id}")
        self.settings = dict(DEFAULT_SETTINGS)
        self.plans: dict[str, dict] = {}
        self.last_error: str | None = None
        self._listeners: list = []
        self._unsubs: list = []
        self._last_desired = False

    # --- úložiště a posluchači -------------------------------------------------

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.settings.update(data.get("settings", {}))
        self.plans = data.get("plans", {})

    async def _async_save(self) -> None:
        today = dt_util.now().date()
        # Staré plány nedržíme
        self.plans = {d: p for d, p in self.plans.items() if date.fromisoformat(d) >= today - timedelta(days=1)}
        await self._store.async_save({"settings": self.settings, "plans": self.plans})

    @callback
    def async_add_listener(self, update_callback) -> callable:
        self._listeners.append(update_callback)
        return lambda: self._listeners.remove(update_callback)

    @callback
    def _notify(self) -> None:
        for cb in list(self._listeners):
            cb()

    def start(self) -> None:
        """Časovače: kontrola každou čtvrthodinu, přepočet ve 23:50, reakce na nové ceny."""
        self._unsubs.append(async_track_time_change(
            self.hass, self._async_on_quarter, minute=[0, 15, 30, 45], second=5))
        self._unsubs.append(async_track_time_change(
            self.hass, self._async_on_evening, hour=23, minute=50, second=0))
        if self.price_entity:
            self._unsubs.append(async_track_state_change_event(
                self.hass, [self.price_entity], self._async_on_prices))
        self.hass.async_create_task(self.async_plan_tomorrow_if_missing())

    def stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    # --- nastavení -------------------------------------------------------------

    async def async_set(self, key: str, value) -> None:
        if self.settings.get(key) == value:
            return
        self.settings[key] = value
        await self._async_save()
        self._notify()
        if key in PLAN_KEYS:
            # Změna nastavení: zítřek se přepočítá sám (pokud už jsou ceny)
            await self.async_compute(dt_util.now().date() + timedelta(days=1))

    # --- vstupy ----------------------------------------------------------------

    def _tank_temp(self) -> float | None:
        if not self.tank_temp_entity:
            return None
        state = self.hass.states.get(self.tank_temp_entity)
        try:
            return float(state.state) if state else None
        except (TypeError, ValueError):
            return None

    def _power_kw(self) -> float:
        power = float(self.settings.get("power_kw") or 0)
        if power <= 0:
            power = float(self.hub.data.get("nominal_power") or 0)
        return power if power > 0 else 100.0

    def _prices(self) -> dict[datetime, float]:
        state = self.hass.states.get(self.price_entity) if self.price_entity else None
        if state is None:
            return {}
        return parse_prices(dict(state.attributes), state.attributes.get("unit_of_measurement"))

    # --- výpočet plánu ---------------------------------------------------------

    async def async_plan_tomorrow_if_missing(self) -> None:
        tomorrow = dt_util.now().date() + timedelta(days=1)
        if tomorrow.isoformat() not in self.plans:
            await self.async_compute(tomorrow, quiet=True)

    async def async_compute(self, day: date, from_now: bool = False, quiet: bool = False) -> None:
        """Spočítá plán pro daný den (from_now = jen zbytek dneška)."""
        s = self.settings
        key = day.isoformat()
        if s["mode"] == MODE_OFF:
            return

        start = dt_util.start_of_local_day(day)
        end = dt_util.start_of_local_day(day + timedelta(days=1))
        quarters = day_quarters(start, end)
        prices = quarter_prices(self._prices(), quarters)
        if all(p is None for p in prices):
            if not quiet:
                _LOGGER.warning("Tedom (%s): Plánovač – ceny pro %s zatím nejsou k dispozici", self.hub._name, key)
            return

        allowed = window_mask(quarters, _minutes(s["window_from"]), _minutes(s["window_to"]))
        allowed = [a and p is not None and (p >= 0 or not s["no_negative"]) for a, p in zip(allowed, prices)]

        max_runs, min_len = int(s["runs"]), int(s["blocks"])
        total = max_runs * min_len
        note = []
        if s["mode"] == MODE_TEMP:
            temp = self._tank_temp()
            if temp is None:
                note.append("teplota nádrže neznámá – plán jako Ručně")
            else:
                total = blocks_for_temperature(total, min_len, temp, float(s["temp_cold"]), float(s["temp_warm"]))
                note.append(f"teplota nádrže {temp:.1f} °C → {total} bloků")

        if from_now:
            now = dt_util.now()
            old = self.plans.get(key, {})
            # Běhy, které už začaly, zůstávají celé (rozjetý běh se nepřeruší)
            done_runs = [(datetime.fromisoformat(a), datetime.fromisoformat(b)) for a, b in old.get("runs", [])
                         if datetime.fromisoformat(a) < now]
            done_blocks = sum(int((b - a) / timedelta(minutes=15)) for a, b in done_runs)
            total = max(0, total - done_blocks)
            max_runs = max(0, max_runs - len(done_runs))
            cutoff = max([now] + [b for _, b in done_runs])
            allowed = [a and q >= cutoff for a, q in zip(allowed, quarters)]

        power = self._power_kw()
        sign = -1.0 if s["strategy"] == STRATEGY_EXPENSIVE else 1.0
        values = [sign * (p or 0.0) * power * 0.25 for p in prices]

        result = await self.hass.async_add_executor_job(
            optimize, values, allowed, max_runs, min_len, total, float(s["penalty"]))

        if result.blocks < total:
            note.append(f"vešlo se jen {result.blocks} z {total} bloků")
            _LOGGER.warning("Tedom (%s): Plánovač %s – %s", self.hub._name, key, note[-1])

        runs = [(quarters[a], quarters[b - 1] + timedelta(minutes=15)) for a, b in result.runs]
        if from_now:
            runs = done_runs + runs
        chosen = [p for a, b in result.runs for p in prices[a:b]]
        self.plans[key] = {
            "runs": [[a.isoformat(), b.isoformat()] for a, b in runs],
            "blocks": result.blocks,
            "starts": len(runs),
            "avg_price": round(sum(chosen) / len(chosen), 3) if chosen else None,
            "value": round(sum(chosen) * power * 0.25, 1) if chosen else 0.0,
            "power_kw": power,
            "note": "; ".join(note) or None,
            "computed_at": dt_util.now().isoformat(),
        }
        await self._async_save()
        self._notify()
        _LOGGER.info("Tedom (%s): Plán %s: %s", self.hub._name, key, self.describe(key))

    # --- dotazy pro entity -----------------------------------------------------

    def runs_for(self, day: date) -> list[tuple[datetime, datetime]]:
        plan = self.plans.get(day.isoformat(), {})
        return [(datetime.fromisoformat(a), datetime.fromisoformat(b)) for a, b in plan.get("runs", [])]

    def describe(self, key: str) -> str:
        plan = self.plans.get(key)
        if plan is None:
            return "Není plán"
        runs = plan.get("runs", [])
        if not runs:
            return "Bez běhu"
        fmt = lambda v: dt_util.as_local(datetime.fromisoformat(v)).strftime("%H:%M")
        return ", ".join(f"{fmt(a)}–{fmt(b)}" for a, b in runs)

    def should_run(self, when: datetime | None = None) -> bool:
        when = when or dt_util.now()
        return any(a <= when < b for a, b in self.runs_for(when.date()))

    def next_start(self) -> datetime | None:
        now = dt_util.now()
        starts = [a for d in (now.date(), now.date() + timedelta(days=1)) for a, _ in self.runs_for(d) if a > now]
        return min(starts) if starts else None

    # --- řízení jednotky -------------------------------------------------------

    async def _async_on_prices(self, event: Event) -> None:
        await self.async_plan_tomorrow_if_missing()

    async def _async_on_evening(self, now: datetime) -> None:
        # Režim podle teploty: zítřek přepočítat s aktuální teplotou nádrže
        if self.settings["mode"] == MODE_TEMP:
            await self.async_compute(now.date() + timedelta(days=1))

    async def _async_on_quarter(self, now: datetime) -> None:
        self._notify()  # "běžet teď", "další start"
        if self.settings["mode"] == MODE_OFF:
            self._last_desired = False
            return

        desired = self.should_run(now)
        temp = self._tank_temp()
        if desired and temp is not None and temp >= float(self.settings["temp_safety"]):
            _LOGGER.warning("Tedom (%s): Plánovač – nádrž %.1f °C ≥ pojistka, blok přeskočen", self.hub._name, temp)
            desired = False

        rpm = self.hub.data.get("rpm")
        if rpm is None:
            return  # stav jednotky neznámý – raději nic
        running = rpm > 0

        try:
            if desired and not running:
                await self._async_command("cmd_engine_start")
            elif not desired and running and self._last_desired:
                # Vypínáme jen na konci naplánovaného běhu – ruční běh mimo plán necháme
                await self._async_command("cmd_engine_stop")
            self.last_error = None
        except HomeAssistantError as err:
            self.last_error = str(err)
            _LOGGER.warning("Tedom (%s): Plánovač – %s", self.hub._name, err)
        self._last_desired = desired
        self._notify()

    async def _async_command(self, key: str) -> None:
        desc = next(d for d in self.hub.plugin.BUTTON_TYPES if d.key == key)
        _LOGGER.info("Tedom (%s): Plánovač – %s", self.hub._name, desc.name)
        await self.hub.async_send_command(desc.command, desc.command_return)
