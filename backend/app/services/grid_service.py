import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple
from backend.app.models.sensor import SensorReading
from backend.app.services.risk_service import calculate_risk_score

CELL_SIZE = {
    "x": 5.0,
    "y": 5.0,
    "z": 1.0,
}

RISK_ZONE_MIN_SCORE = 25.0

CellKey = Tuple[float, float, float]

def get_value(obj: Any, field: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field)

def format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value).replace(".", "p")

def format_cell_id(cell_key: CellKey) -> str:
    x, y, z = cell_key
    return f"x{format_number(x)}_y{format_number(y)}_z{format_number(z)}"

def get_cell_key(position: Any) -> CellKey:
    x = float(get_value(position, "x"))
    y = float(get_value(position, "y"))
    z = float(get_value(position, "z"))

    cell_x = math.floor(x / CELL_SIZE["x"]) * CELL_SIZE["x"]
    cell_y = math.floor(y / CELL_SIZE["y"]) * CELL_SIZE["y"]
    cell_z = math.floor(z / CELL_SIZE["z"]) * CELL_SIZE["z"]

    return cell_x, cell_y, cell_z

def get_cell_center(cell_key: CellKey) -> Dict[str, float]:
    x, y, z = cell_key

    return {
        "x": x + CELL_SIZE["x"] / 2.0,
        "y": y + CELL_SIZE["y"] / 2.0,
        "z": z + CELL_SIZE["z"] / 2.0,
    }

def average(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)

def build_average_gas(readings: List[SensorReading]) -> Dict[str, float]:
    return {
        "ch4_ppm": round(average([r.gas.ch4_ppm for r in readings]), 2),
        "co_ppm": round(average([r.gas.co_ppm for r in readings]), 2),
        "co2_ppm": round(average([r.gas.co2_ppm for r in readings]), 2),
        "o2_percent": round(average([r.gas.o2_percent for r in readings]), 2),
    }

def build_representative_reading(latest_reading: SensorReading,gas_avg: Dict[str, float],center: Dict[str, float]) -> SensorReading:
    """
    Creates one representative reading for a grid cell.

    Metadata, lidar and source come from the latest reading in the cell.
    Gas values are averaged.
    Position becomes the cell center.
    """
    gas_copy = latest_reading.gas.model_copy(update=gas_avg)
    position_copy = latest_reading.position.model_copy(update=center)

    return latest_reading.model_copy(
        deep=True,
        update={"gas": gas_copy,"position": position_copy},
    )

def build_cell_summary(cell_key: CellKey, readings: List[SensorReading]) -> Dict:
    sorted_readings = sorted(readings, key=lambda r: r.timestamp)
    latest_reading = sorted_readings[-1]

    center = get_cell_center(cell_key)
    gas_avg = build_average_gas(sorted_readings)

    representative_reading = build_representative_reading(latest_reading=latest_reading,gas_avg=gas_avg,center=center)

    risk = calculate_risk_score(representative_reading,recent_readings=sorted_readings)

    sources = sorted({reading.source for reading in sorted_readings})
    drone_ids = sorted({reading.drone_id for reading in sorted_readings})

    return {
        "cell_id": format_cell_id(cell_key),
        "cell_origin": {
            "x": cell_key[0],
            "y": cell_key[1],
            "z": cell_key[2],
        },
        "center": center,
        "sample_count": len(sorted_readings),
        "sources": sources,
        "drone_ids": drone_ids,
        "first_seen": sorted_readings[0].timestamp.isoformat(),
        "last_seen": latest_reading.timestamp.isoformat(),
        "gas_avg": gas_avg,
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "alarm_level": risk["alarm_level"],
        "safety_status": risk["safety_status"],
        "recommended_action": risk["recommended_action"],
        "reasons": risk["reasons"],
        "warnings": risk["warnings"],
        "score_breakdown": risk["score_breakdown"],
    }


def build_3d_risk_map(readings: List[SensorReading]) -> Dict:
    cells: Dict[CellKey, List[SensorReading]] = defaultdict(list)

    for reading in readings:
        cell_key = get_cell_key(reading.position)
        cells[cell_key].append(reading)

    cell_summaries = [
        build_cell_summary(cell_key, cell_readings)
        for cell_key, cell_readings in cells.items()
    ]

    cell_summaries.sort(
        key=lambda cell: (
            cell["risk_score"],
            cell["sample_count"],
        ),
        reverse=True,
    )

    return {
        "cell_size": CELL_SIZE,
        "cell_count": len(cell_summaries),
        "risk_zone_min_score": RISK_ZONE_MIN_SCORE,
        "cells": cell_summaries,
    }


def get_risk_zones(readings: List[SensorReading]) -> List[Dict]:
    risk_map = build_3d_risk_map(readings)

    zones = [
        cell
        for cell in risk_map["cells"]
        if cell["risk_score"] >= RISK_ZONE_MIN_SCORE
    ]

    zones.sort(key=lambda zone: zone["risk_score"], reverse=True)

    return zones