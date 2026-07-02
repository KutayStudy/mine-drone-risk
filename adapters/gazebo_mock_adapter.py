import math
import time
from datetime import datetime, timezone
import requests

BACKEND_URL = "http://127.0.0.1:8000/api/readings"

def distance_3d(position, source):
    return math.sqrt((position["x"] - source["x"]) ** 2 + (position["y"] - source["y"]) ** 2 + (position["z"] - source["z"]) ** 2)

def generate_mock_gas(position):
    ch4_ppm = 3000
    co_ppm = 5
    co2_ppm = 400
    o2_percent = 20.8

    methane_source = {"x": 12.0, "y": 5.0, "z": 2.5}
    methane_distance = distance_3d(position, methane_source)

    ch4_ppm = max(ch4_ppm, 38000 / (1 + methane_distance))

    if position["z"] >= 2.0 and methane_distance < 4.0:
        ch4_ppm += 8000

    co_source = {"x": 20.0, "y": 5.0, "z": 1.2}
    co_distance = distance_3d(position, co_source)
    co_ppm = max(co_ppm, 120 / (1 + co_distance))

    oxygen_drop_source = {"x": 22.0, "y": 5.0, "z": 1.2}
    oxygen_distance = distance_3d(position, oxygen_drop_source)

    if oxygen_distance < 5.0:
        o2_percent = 20.8 - ((5.0 - oxygen_distance) * 0.6)

    co2_ppm = 400 + max(0, (5.0 - oxygen_distance) * 120)

    return {
        "ch4_ppm": round(ch4_ppm, 2),
        "co_ppm": round(co_ppm, 2),
        "co2_ppm": round(co2_ppm, 2),
        "o2_percent": round(o2_percent, 2),
    }


def generate_mock_lidar(position):
    if 21 <= position["x"] <= 24:
        return {
            "min_distance": 0.4,
            "front_distance": 0.4,
            "left_distance": 0.8,
            "right_distance": 0.9,
            "ceiling_distance": 0.7,
            "floor_distance": 1.2,
            "obstacle_density": 0.6,
        }

    return {
        "min_distance": 2.0,
        "front_distance": 2.5,
        "left_distance": 2.0,
        "right_distance": 2.0,
        "ceiling_distance": 2.2,
        "floor_distance": 1.0,
        "obstacle_density": 0.2,
    }


def generate_mock_imu(step):
    return {
        "roll": 0.0,
        "pitch": 0.0,
        "yaw": round(step * 0.05, 2),
    }


def create_payload(position, step):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "drone_id": "drone-1",
        "source": "gazebo",
        "position": position,
        "gas": generate_mock_gas(position),
        "imu": generate_mock_imu(step),
        "lidar": generate_mock_lidar(position),
        "battery": 90 - step,
    }


def send_reading(payload):
    response = requests.post(BACKEND_URL, json=payload, timeout=5)
    response.raise_for_status()
    return response.json()


def main():
    route = [
        {"x": 2.0, "y": 5.0, "z": 1.2},
        {"x": 6.0, "y": 5.0, "z": 1.4},
        {"x": 10.0, "y": 5.0, "z": 1.8},
        {"x": 12.0, "y": 5.0, "z": 2.5},
        {"x": 15.0, "y": 5.0, "z": 2.0},
        {"x": 20.0, "y": 5.0, "z": 1.2},
        {"x": 22.0, "y": 5.0, "z": 1.2},
    ]

    for step, position in enumerate(route):
        payload = create_payload(position, step)

        print("\nSending reading:")
        print(payload)

        result = send_reading(payload)

        print("Backend response:")
        print(result)

        time.sleep(2)

if __name__ == "__main__":
    main()