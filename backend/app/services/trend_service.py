"""
Temporal trend analysis for the mine drone prototype.

All change-rate limits are HEURISTIC/PROTOTYPE: there is no regulatory
ppm-per-second standard. The values in thresholds.TREND_RATE_LIMITS are
sensitivities chosen so that a sustained rate would cross the sourced
absolute thresholds (MSHA/NIOSH) within minutes.

Response contract kept from v0.1 (trend_available, window_size,
elapsed_seconds, trend_warnings, change_rates with the same keys) with
two additive fields: change_rates_per_minute and consistency_warnings.
"""

from typing import Dict, List
from backend.app.models.sensor import SensorReading
from backend.app.services import thresholds as T

RATES = T.TREND_RATE_LIMITS

def calculate_change_rate(old_value: float,new_value: float,elapsed_seconds: float,) -> float:
    if elapsed_seconds <= 0:
        return 0.0
    return (new_value - old_value) / elapsed_seconds


def analyze_temporal_trend(readings: List[SensorReading],window_size: int = 3) -> Dict:
    if len(readings) < 2:
        return {
            "trend_available": False,
            "window_size": len(readings),
            "elapsed_seconds": 0.0,
            "trend_warnings": [],
            "change_rates": {},
            "change_rates_per_minute": {},
            "consistency_warnings": [],
        }

    latest_reading = readings[-1]

    same_drone_readings = [
        reading for reading in readings
        if reading.drone_id == latest_reading.drone_id
    ]

    if len(same_drone_readings) < 2:
        return {
            "trend_available": False,
            "window_size": len(same_drone_readings),
            "elapsed_seconds": 0.0,
            "trend_warnings": [],
            "change_rates": {},
            "change_rates_per_minute": {},
            "consistency_warnings": [],
        }

    recent = same_drone_readings[-window_size:]
    first = recent[0]
    last = recent[-1]
    elapsed_seconds = (last.timestamp - first.timestamp).total_seconds()

    # Guard against sub-second / zero windows: rates computed over tiny
    # intervals amplify sensor noise into false "rapid increase" warnings.
    if elapsed_seconds < T.MIN_TREND_ELAPSED_SECONDS:
        return {
            "trend_available": False,
            "window_size": len(recent),
            "elapsed_seconds": elapsed_seconds,
            "trend_warnings": [],
            "change_rates": {},
            "change_rates_per_minute": {},
            "consistency_warnings": [
                "Trend window too short for reliable rate estimation"
            ],
        }

    ch4_rate = calculate_change_rate(first.gas.ch4_ppm,last.gas.ch4_ppm,elapsed_seconds)
    co_rate = calculate_change_rate(first.gas.co_ppm,last.gas.co_ppm,elapsed_seconds)
    co2_rate = calculate_change_rate(first.gas.co2_ppm,last.gas.co2_ppm,elapsed_seconds)
    o2_rate = calculate_change_rate(first.gas.o2_percent,last.gas.o2_percent,elapsed_seconds)

    trend_warnings: List[str] = []
    consistency_warnings: List[str] = []

    # HEURISTIC/PROTOTYPE rate limits - see thresholds.TREND_RATE_LIMITS.
    ch4_rising = ch4_rate > RATES["ch4_ppm_per_second"]
    co_rising = co_rate > RATES["co_ppm_per_second"]
    co2_rising = co2_rate > RATES["co2_ppm_per_second"]
    o2_falling = o2_rate < RATES["o2_percent_per_second"]

    if ch4_rising:
        trend_warnings.append("Methane concentration is increasing rapidly")

    if co_rising:
        trend_warnings.append("Carbon monoxide concentration is increasing rapidly")

    if co2_rising:
        trend_warnings.append("Carbon dioxide concentration is increasing rapidly")

    if o2_falling:
        trend_warnings.append("Oxygen level is decreasing over time")

    if ch4_rising and o2_falling:
        trend_warnings.append("Methane increase combined with oxygen decrease trend")

    # Consistency check (HEURISTIC/PROTOTYPE): a falling O2 signal with no
    # movement at all in CH4/CO/CO2 suggests O2 sensor drift rather than a
    # real displacement event - something must be displacing the oxygen.
    others_flat = (
        abs(ch4_rate) < 0.1 * RATES["ch4_ppm_per_second"]
        and abs(co_rate) < 0.1 * RATES["co_ppm_per_second"]
        and abs(co2_rate) < 0.1 * RATES["co2_ppm_per_second"]
    )

    if o2_falling and others_flat:
        consistency_warnings.append(
            "O2 is falling while CH4/CO/CO2 are flat; possible O2 sensor "
            "drift or an unmeasured displacing gas"
        )

    return {
        "trend_available": True,
        "window_size": len(recent),
        "elapsed_seconds": elapsed_seconds,
        "trend_warnings": trend_warnings,
        "change_rates": {
            "ch4_ppm_per_second": ch4_rate,
            "co_ppm_per_second": co_rate,
            "co2_ppm_per_second": co2_rate,
            "o2_percent_per_second": o2_rate,
        },
        "change_rates_per_minute": {
            "ch4_ppm_per_minute": ch4_rate * 60.0,
            "co_ppm_per_minute": co_rate * 60.0,
            "co2_ppm_per_minute": co2_rate * 60.0,
            "o2_percent_per_minute": o2_rate * 60.0,
        },
        "consistency_warnings": consistency_warnings,
    }