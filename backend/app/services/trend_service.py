from typing import Dict, List
from backend.app.models.sensor import SensorReading

def calculate_change_rate(old_value: float,new_value: float,elapsed_seconds: float) -> float:
    if elapsed_seconds <= 0:
        return 0.0

    return (new_value - old_value) / elapsed_seconds

def analyze_temporal_trend(readings: List[SensorReading], window_size: int = 3) -> Dict:
    if len(readings) < 2:
        return {
            "trend_available": False,
            "trend_warnings": [],
            "change_rates": {}}

    recent = readings[-window_size:]
    first = recent[0]
    last = recent[-1]

    elapsed_seconds = (last.timestamp - first.timestamp).total_seconds()

    ch4_rate = calculate_change_rate(first.gas.ch4_ppm,last.gas.ch4_ppm,elapsed_seconds)
    co_rate = calculate_change_rate(first.gas.co_ppm,last.gas.co_ppm,elapsed_seconds)
    co2_rate = calculate_change_rate(first.gas.co2_ppm,last.gas.co2_ppm,elapsed_seconds)
    o2_rate = calculate_change_rate(first.gas.o2_percent,last.gas.o2_percent,elapsed_seconds)

    trend_warnings = []

    if ch4_rate > 100:
        trend_warnings.append("Methane concentration is increasing rapidly")
    if co_rate > 1:
        trend_warnings.append("Carbon monoxide concentration is increasing rapidly")
    if co2_rate > 50:
        trend_warnings.append("Carbon dioxide concentration is increasing rapidly")
    if o2_rate < -0.02:
        trend_warnings.append("Oxygen level is decreasing over time")
    if ch4_rate > 100 and o2_rate < -0.02:
        trend_warnings.append("Methane increase combined with oxygen decrease trend")

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
        }
    }