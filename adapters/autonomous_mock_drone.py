import time
from datetime import datetime, timezone
from typing import Dict, List
import requests
from gas_field_simulator import (generate_environment,generate_gas,generate_imu,generate_lidar)

BACKEND_URL = "http://127.0.0.1:8000"
DRONE_ID = "mock-drone-1"

ROUTE: List[Dict[str, float]] = [
    # Normal air region
    {"x": 2.0, "y": 5.0, "z": 1.2},
    {"x": 5.0, "y": 5.0, "z": 1.2},
    {"x": 8.0, "y": 5.0, "z": 1.5},

    # Upper methane pocket
    {"x": 10.0, "y": 5.0, "z": 2.0},
    {"x": 12.0, "y": 5.0, "z": 2.5},
    {"x": 14.0, "y": 5.0, "z": 2.3},

    # CO zone
    {"x": 18.0, "y": 5.0, "z": 1.2},
    {"x": 20.0, "y": 5.0, "z": 1.2},

    # O2 drop + obstacle zone
    {"x": 22.0, "y": 5.0, "z": 1.2},
    {"x": 24.0, "y": 5.0, "z": 1.2},
]

def build_payload(position: Dict[str, float], step: int) -> Dict:
    environment = generate_environment(position)

    return {
        "drone_id": DRONE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "mock",
        "position": position,
        "gas": generate_gas(position),
        "lidar": generate_lidar(position),
        "environment": {
            "temperature": environment["temperature_c"],
            "humidity": environment["humidity_percent"],
            "pressure": environment["pressure_hpa"],
        },
        "imu": generate_imu(step),
        "battery": max(20.0, 100.0 - step * 1.5),
    }

def post_reading(payload: Dict) -> None:
    url = f"{BACKEND_URL}/api/readings"

    try:
        response = requests.post(url, json=payload, timeout=5)
    except requests.RequestException as exc:
        print(f"[ERROR] Could not reach backend: {exc}")
        return

    if response.status_code not in (200, 201):
        print(f"[ERROR] POST /api/readings failed: {response.status_code}")
        print(response.text)
        return

    print(
        "[OK] reading posted | "
        f"x={payload['position']['x']} "
        f"z={payload['position']['z']} | "
        f"CH4={payload['gas']['ch4_ppm']} ppm | "
        f"CO={payload['gas']['co_ppm']} ppm | "
        f"O2={payload['gas']['o2_percent']}%")

def run_mission(delay_seconds: float = 1.0) -> None:
    print("[INFO] Autonomous mock drone started")
    print(f"[INFO] Backend URL: {BACKEND_URL}")
    print(f"[INFO] Route points: {len(ROUTE)}")

    for step, position in enumerate(ROUTE):
        payload = build_payload(position, step)
        post_reading(payload)
        time.sleep(delay_seconds)

    print("[INFO] Mock drone route completed")

if __name__ == "__main__":
    run_mission()