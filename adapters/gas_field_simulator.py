import math
import random
from typing import Dict, Optional

def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))

def distance_3d(position: Dict[str, float], source: Dict[str, float]) -> float:
    return math.sqrt((position["x"] - source["x"]) ** 2 + (position["y"] - source["y"]) ** 2 + (position["z"] - source["z"]) ** 2)

def gaussian_influence(distance: float, sigma: float) -> float:
    if sigma <= 0:
        return 0.0

    return math.exp(-(distance ** 2) / (2 * sigma ** 2))

def small_noise(scale: float) -> float:
    return random.uniform(-scale, scale)

def generate_gas(position: Dict[str, float],seed: Optional[int] = None) -> Dict[str, float]:
    """
    Synthetic gas field for the mine/drone demo.

    Units:
    - CH4, CO, CO2: ppm
    - O2: percent
    """
    if seed is not None:
        random.seed(seed)

    x = float(position["x"])
    y = float(position["y"])
    z = float(position["z"])

    ch4_ppm = 3000.0
    co_ppm = 5.0
    co2_ppm = 450.0
    o2_percent = 20.9

    # 1) Upper-volume methane pocket
    methane_source = {"x": 12.0, "y": 5.0, "z": 2.6}
    methane_distance = distance_3d(position, methane_source)
    methane_strength = gaussian_influence(methane_distance, sigma=3.0)

    upper_volume_bonus = 1.35 if z >= 2.0 else 1.0
    ch4_ppm += 32_000.0 * methane_strength * upper_volume_bonus

    # 2) Carbon monoxide zone
    co_source = {"x": 20.0, "y": 5.0, "z": 1.2}
    co_distance = distance_3d(position, co_source)
    co_strength = gaussian_influence(co_distance, sigma=2.2)

    co_ppm += 130.0 * co_strength

    # 3) Poorly ventilated oxygen-drop zone
    low_o2_source = {"x": 22.0, "y": 5.0, "z": 1.2}
    low_o2_distance = distance_3d(position, low_o2_source)
    low_o2_strength = gaussian_influence(low_o2_distance, sigma=2.8)

    o2_percent -= 2.2 * low_o2_strength
    co2_ppm += 1600.0 * low_o2_strength

    # 4) Sensor-like noise
    ch4_ppm += small_noise(150.0)
    co_ppm += small_noise(1.5)
    co2_ppm += small_noise(20.0)
    o2_percent += small_noise(0.03)

    ch4_ppm = clamp(ch4_ppm, 0.0, 60_000.0)
    co_ppm = clamp(co_ppm, 0.0, 1_500.0)
    co2_ppm = clamp(co2_ppm, 350.0, 50_000.0)
    o2_percent = clamp(o2_percent, 15.0, 21.0)

    return {
        "ch4_ppm": round(ch4_ppm, 2),
        "co_ppm": round(co_ppm, 2),
        "co2_ppm": round(co2_ppm, 2),
        "o2_percent": round(o2_percent, 2),
    }


def generate_lidar(position: Dict[str, float]) -> Dict[str, float]:
    """
    Simple LiDAR summary for backend SensorReading.lidar.
    This is not raw point cloud simulation.
    """
    x = float(position["x"])
    z = float(position["z"])

    # Narrow / blocked zone
    if 21.0 <= x <= 24.0:
        return {
            "min_distance": 0.4,
            "front_distance": 0.4,
            "left_distance": 0.8,
            "right_distance": 0.9,
            "ceiling_distance": 0.7,
            "floor_distance": max(0.2, z),
            "obstacle_density": 0.65,
        }

    # Upper methane zone with lower ceiling clearance
    if 10.0 <= x <= 15.0 and z >= 2.0:
        return {
            "min_distance": 1.2,
            "front_distance": 2.0,
            "left_distance": 1.8,
            "right_distance": 1.7,
            "ceiling_distance": 0.9,
            "floor_distance": max(0.2, z),
            "obstacle_density": 0.25,
        }

    return {
        "min_distance": 2.0,
        "front_distance": 2.5,
        "left_distance": 2.0,
        "right_distance": 2.0,
        "ceiling_distance": 2.2,
        "floor_distance": max(0.2, z),
        "obstacle_density": 0.1,
    }


def generate_environment(position: Dict[str, float]) -> Dict[str, float]:
    x = float(position["x"])

    return {
        "temperature_c": round(24.0 + 0.05 * x + small_noise(0.2), 2),
        "humidity_percent": round(55.0 + small_noise(2.0), 2),
        "pressure_hpa": round(1012.0 + small_noise(0.8), 2),
    }


def generate_imu(step: int = 0) -> Dict[str, float]:
    return {
        "roll": 0.0,
        "pitch": 0.0,
        "yaw": round(step * 0.05, 2),
    }