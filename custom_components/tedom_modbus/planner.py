"""Plánovač běhu kogenerace podle spotových cen (čistý Python, bez závislosti na HA).

Den se dělí na čtvrthodiny. Hledá se nejvýhodnější sada běhů:
  * každý běh má aspoň `min_len` čtvrthodin,
  * běhů je nejvýš `max_runs`,
  * celkem se naplánuje `total` čtvrthodin (pokud se nevejdou, co nejvíc),
  * běh smí ležet jen v povolených čtvrthodinách (okno od–do, záporné ceny),
  * každý start stojí `start_penalty` – více startů jen tehdy, když se vyplatí.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import math

QUARTER = timedelta(minutes=15)


@dataclass
class PlanResult:
    runs: list[tuple[int, int]]  # (začátek, konec) jako indexy čtvrthodin, konec je exkluzivní
    blocks: int
    cost: float  # součet cen běhů + penalizace startů (v "nákladovém" smyslu strategie)


def optimize(
    values: list[float],
    allowed: list[bool],
    max_runs: int,
    min_len: int,
    total: int,
    start_penalty: float,
) -> PlanResult:
    """Najde runy s minimálním součtem `values` + penalizací startů.

    `values` jsou náklady čtvrthodin (pro strategii "nejdražší" záporná cena).
    Přednost má co nejvíc bloků (až `total`), pak nejnižší náklad, pak méně startů.
    """
    n = len(values)
    total = max(0, min(total, n))
    max_runs = max(0, max_runs)
    min_len = max(1, min_len)
    # Nepatrná přirážka za start: při shodě vyhraje méně startů
    pen = start_penalty + 1e-6

    # Počet po sobě jdoucích povolených čtvrthodin od indexu t
    run_room = [0] * (n + 1)
    for t in range(n - 1, -1, -1):
        run_room[t] = run_room[t + 1] + 1 if allowed[t] else 0

    prefix = [0.0] * (n + 1)
    for t in range(n):
        prefix[t + 1] = prefix[t] + values[t]

    inf = math.inf
    # g[t][k][r] = min. náklad naplánovat přesně k bloků v [t, n) s nejvýš r běhy
    g = [[[inf] * (max_runs + 1) for _ in range(total + 1)] for _ in range(n + 1)]
    for r in range(max_runs + 1):
        g[n][0][r] = 0.0

    for t in range(n - 1, -1, -1):
        gt, gnext = g[t], g[t + 1]
        room = run_room[t]
        for k in range(total + 1):
            row = gt[k]
            skip = gnext[k]
            for r in range(max_runs + 1):
                best = skip[r]
                if r > 0 and k >= min_len and room >= min_len:
                    for length in range(min_len, min(room, k) + 1):
                        rest = g[t + length][k - length][r - 1]
                        if rest < inf:
                            c = prefix[t + length] - prefix[t] + pen + rest
                            if c < best:
                                best = c
                row[r] = best

    # Co nejvíc bloků, pokud se celý požadavek nevejde
    blocks = next((k for k in range(total, -1, -1) if g[0][k][max_runs] < inf), 0)

    runs: list[tuple[int, int]] = []
    t, k, r = 0, blocks, max_runs
    while k > 0:
        target = g[t][k][r]
        if g[t + 1][k][r] == target:
            t += 1
            continue
        for length in range(min_len, min(run_room[t], k) + 1):
            rest = g[t + length][k - length][r - 1]
            if rest < inf and abs(prefix[t + length] - prefix[t] + pen + rest - target) < 1e-9:
                runs.append((t, t + length))
                t, k, r = t + length, k - length, r - 1
                break
        else:  # pragma: no cover - nemělo by nastat
            raise RuntimeError("Plánovač: rekonstrukce plánu selhala")

    cost = g[0][blocks][max_runs] - 1e-6 * len(runs) if blocks else 0.0
    return PlanResult(runs=runs, blocks=blocks, cost=cost)


def parse_prices(attributes: dict, unit: str | None) -> dict[datetime, float]:
    """Ceny z atributů senzoru (klíč = čas ISO 8601) převedené na cenu za kWh."""
    divisor = 1000.0 if unit and "mwh" in unit.lower() else 1.0
    prices: dict[datetime, float] = {}
    for key, value in attributes.items():
        try:
            when = key if isinstance(key, datetime) else datetime.fromisoformat(str(key))
            price = float(value)
        except (TypeError, ValueError):
            continue
        if when.tzinfo is None:
            continue
        prices[when] = price / divisor
    return prices


def day_quarters(day_start: datetime, day_end: datetime) -> list[datetime]:
    """Začátky čtvrthodin mezi dvěma lokálními půlnocemi (počítá i se změnou času)."""
    quarters = []
    t = day_start
    while t < day_end:
        quarters.append(t)
        t = t + QUARTER
    return quarters


def quarter_prices(prices: dict[datetime, float], quarters: list[datetime]) -> list[float | None]:
    """Cena pro každou čtvrthodinu – z 15min ceny, nebo z hodinové ceny, do které spadá."""
    if not prices:
        return [None] * len(quarters)
    ordered = sorted(prices)
    step = min((b - a for a, b in zip(ordered, ordered[1:])), default=timedelta(hours=1))
    result: list[float | None] = []
    for q in quarters:
        price = prices.get(q)
        if price is None and step >= timedelta(hours=1):
            hour = q - timedelta(minutes=q.minute % 60, seconds=q.second)
            price = prices.get(hour)
        result.append(price)
    return result


def window_mask(quarters: list[datetime], start_minutes: int, end_minutes: int) -> list[bool]:
    """Povolené čtvrthodiny podle okna od–do (může jít přes půlnoc; od == do = celý den)."""
    if start_minutes == end_minutes:
        return [True] * len(quarters)
    mask = []
    for q in quarters:
        m = q.hour * 60 + q.minute
        if start_minutes < end_minutes:
            mask.append(start_minutes <= m < end_minutes)
        else:
            mask.append(m >= start_minutes or m < end_minutes)
    return mask


def blocks_for_temperature(max_blocks: int, min_len: int, temp: float, cold: float, warm: float) -> int:
    """Počet bloků lineárně od max_blocks (studená nádrž) po 0 (teplá nádrž)."""
    if warm <= cold:
        return max_blocks if temp < warm else 0
    ratio = (warm - temp) / (warm - cold)
    blocks = round(max_blocks * min(1.0, max(0.0, ratio)))
    if 0 < blocks < min_len:
        blocks = min_len  # jeden běh musí mít aspoň min. délku
    return blocks
