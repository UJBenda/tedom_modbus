"""Entity plánovače podle spotových cen (nastavení, plán, tlačítka přepočtu)."""
from __future__ import annotations

from datetime import time, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory, UnitOfPower, UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .plugin_tedom import TedomPlugin
from .spot_planner import MODES, STRATEGIES, TedomSpotPlanner


class PlannerEntity:
    """Společný základ: zařízení jednotky, unique_id, obnovování při změně plánu."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, planner: TedomSpotPlanner, key: str, name: str, icon: str | None = None) -> None:
        self.planner = planner
        self._key = key
        self._attr_unique_id = f"{planner.hub._name}_plan_{key}".lower()
        self._attr_name = name
        self._attr_icon = icon

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.planner.hub._name)},
            name=self.planner.hub._name,
            manufacturer="Tedom",
            model=TedomPlugin.NAME,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.planner.async_add_listener(self.async_write_ha_state))


# --- Nastavení ---------------------------------------------------------------

class PlannerSelect(PlannerEntity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, planner, key, name, options: dict, icon):
        super().__init__(planner, key, name, icon)
        self._map = options
        self._attr_options = list(options.values())

    @property
    def current_option(self):
        return self._map.get(self.planner.settings[self._key])

    async def async_select_option(self, option: str) -> None:
        value = next(k for k, v in self._map.items() if v == option)
        await self.planner.async_set(self._key, value)


class PlannerNumber(PlannerEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, planner, key, name, icon, min_value, max_value, step, unit=None):
        super().__init__(planner, key, name, icon)
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return self.planner.settings[self._key]

    async def async_set_native_value(self, value: float) -> None:
        if self._attr_native_step >= 1:
            value = int(value)
        await self.planner.async_set(self._key, value)


class PlannerTime(PlannerEntity, TimeEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> time:
        h, m = str(self.planner.settings[self._key]).split(":")[:2]
        return time(int(h), int(m))

    async def async_set_value(self, value: time) -> None:
        await self.planner.async_set(self._key, value.strftime("%H:%M"))


class PlannerSwitch(PlannerEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        return bool(self.planner.settings[self._key])

    async def async_turn_on(self, **kwargs) -> None:
        await self.planner.async_set(self._key, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.planner.async_set(self._key, False)


# --- Plán --------------------------------------------------------------------

class PlanDaySensor(PlannerEntity, SensorEntity):
    """Stav = časy běhů (např. "07:00–08:45, 18:00–19:00"), detaily v atributech."""

    def __init__(self, planner, key, name, day_offset: int):
        super().__init__(planner, key, name, "mdi:calendar-clock")
        self._offset = day_offset

    def _day_key(self) -> str:
        return (dt_util.now().date() + timedelta(days=self._offset)).isoformat()

    @property
    def native_value(self) -> str:
        return self.planner.describe(self._day_key())[:255]

    @property
    def extra_state_attributes(self):
        plan = self.planner.plans.get(self._day_key(), {})
        return {
            "starty": plan.get("starts"),
            "bloky": plan.get("blocks"),
            "prumerna_cena": plan.get("avg_price"),
            "hodnota_elektriny": plan.get("value"),
            "vykon_kw": plan.get("power_kw"),
            "poznamka": plan.get("note"),
            "spocitano": plan.get("computed_at"),
            "behy": plan.get("runs", []),
            "posledni_chyba": self.planner.last_error,
        }


class PlanNextStartSensor(PlannerEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        return self.planner.next_start()


class PlanRunNowBinarySensor(PlannerEntity, BinarySensorEntity):
    @property
    def is_on(self) -> bool:
        return self.planner.settings["mode"] != "off" and self.planner.should_run()


class PlanRecomputeButton(PlannerEntity, ButtonEntity):
    def __init__(self, planner, key, name, icon, rest_of_today: bool):
        super().__init__(planner, key, name, icon)
        self._rest_of_today = rest_of_today

    async def async_press(self) -> None:
        today = dt_util.now().date()
        if self._rest_of_today:
            await self.planner.async_compute(today, from_now=True)
        else:
            await self.planner.async_compute(today + timedelta(days=1))


# --- Seznamy pro jednotlivé platformy ----------------------------------------

def selects(p):
    return [
        PlannerSelect(p, "mode", "Plánovač režim", MODES, "mdi:calendar-sync"),
        PlannerSelect(p, "strategy", "Plánovač strategie", STRATEGIES, "mdi:chart-line"),
    ]


def numbers(p):
    return [
        PlannerNumber(p, "runs", "Plánovač počet startů", "mdi:counter", 1, 10, 1),
        PlannerNumber(p, "blocks", "Plánovač bloky na běh (15 min)", "mdi:timer-sand", 1, 16, 1),
        PlannerNumber(p, "penalty", "Plánovač cena startu", "mdi:cash", 0, 5000, 10, "Kč"),
        PlannerNumber(p, "power_kw", "Plánovač výkon (0 = jmenovitý)", "mdi:lightning-bolt", 0, 5000, 1, UnitOfPower.KILO_WATT),
        PlannerNumber(p, "temp_cold", "Plánovač teplota nádrže – plný běh", "mdi:thermometer-low", 0, 120, 1, UnitOfTemperature.CELSIUS),
        PlannerNumber(p, "temp_warm", "Plánovač teplota nádrže – bez běhu", "mdi:thermometer-high", 0, 120, 1, UnitOfTemperature.CELSIUS),
        PlannerNumber(p, "temp_safety", "Plánovač pojistka max. teploty", "mdi:thermometer-alert", 0, 120, 1, UnitOfTemperature.CELSIUS),
    ]


def times(p):
    return [
        PlannerTime(p, "window_from", "Plánovač smí běžet od", "mdi:clock-start"),
        PlannerTime(p, "window_to", "Plánovač smí běžet do", "mdi:clock-end"),
    ]


def switches(p):
    return [PlannerSwitch(p, "no_negative", "Plánovač nejet při záporné ceně", "mdi:cash-remove")]


def sensors(p):
    return [
        PlanDaySensor(p, "today", "Plán dnes", 0),
        PlanDaySensor(p, "tomorrow", "Plán zítra", 1),
        PlanNextStartSensor(p, "next_start", "Plán další start", "mdi:clock-outline"),
    ]


def binary_sensors(p):
    return [PlanRunNowBinarySensor(p, "run_now", "Plán běžet teď", "mdi:play-circle-outline")]


def buttons(p):
    return [
        PlanRecomputeButton(p, "recompute_tomorrow", "Přepočítat plán zítřka", "mdi:calendar-refresh", False),
        PlanRecomputeButton(p, "recompute_today", "Přepočítat zbytek dneška", "mdi:calendar-today", True),
    ]
