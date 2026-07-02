# API Contract

## Sources

- `gazebo`: simulated drone/platform
- `esp32`: hardware sensor box
- `mock`: synthetic test data

## Main endpoints

### GET /health

Backend health check.

### POST /api/readings

Saves a sensor reading.

Required format:

```json
{
  "timestamp": "2026-07-02T19:00:00",
  "drone_id": "drone-1",
  "source": "gazebo",
  "position": {"x": 12.0, "y": 5.0, "z": 2.5},
  "gas": {
    "ch4_ppm": 25000,
    "co_ppm": 75,
    "co2_ppm": 600,
    "o2_percent": 19.4
  },
  "imu": {"roll": 0.0, "pitch": 0.0, "yaw": 1.5},
  "lidar": {
    "min_distance": 0.9,
    "front_distance": 2.8,
    "left_distance": 1.1,
    "right_distance": 1.4,
    "ceiling_distance": 1.6,
    "floor_distance": 1.8,
    "obstacle_density": 0.32
  },
  "battery": 74
}
```

### GET /api/readings

Returns latest readings.

### GET /api/readings/{drone_id}

Returns latest readings for a specific drone.

### POST /api/drone/status

Updates current drone/platform status.

### GET /api/drone/status/{drone_id}

Returns current status for a specific drone.

### GET /api/drones/statuses

Returns statuses for all drones.

---

## Risk endpoints

### GET /api/risk/current

Calculates instant rule-based risk from the latest reading.

Evaluates:

- CH4, CO, CO2, O2 thresholds
- O2 drop + CH4 increase combination
- Upper tunnel methane risk using `z`
- LiDAR safety warnings
- Alarm level and recommended action

Example response:

```json
{
  "message": "risk_calculated",
  "risk": {
    "risk_score": 68.0,
    "risk_level": "high",
    "alarm_level": "danger",
    "safety_status": "unsafe_obstacle_detected",
    "recommended_action": "hold_position_and_notify_operator",
    "reasons": [
      "Elevated carbon monoxide level",
      "Critical oxygen drop"
    ],
    "warnings": [
      "Obstacle dangerously close",
      "Low ceiling clearance"
    ],
    "validation_errors": []
  }
}
```

### GET /api/risk/trend

Analyzes temporal gas trends from recent readings.

Example response:

```json
{
  "message": "trend_analyzed",
  "trend": {
    "trend_available": true,
    "window_size": 3,
    "elapsed_seconds": 20.0,
    "trend_warnings": [
      "Methane concentration is increasing rapidly",
      "Oxygen level is decreasing over time",
      "Methane increase combined with oxygen decrease trend"
    ],
    "change_rates": {
      "ch4_ppm_per_second": 350.0,
      "co_ppm_per_second": 0.25,
      "co2_ppm_per_second": 7.5,
      "o2_percent_per_second": -0.06
    }
  }
}
```

---

## Unit rules

CH4, CO and CO2 must be sent as `ppm`.

O2 must be sent as `percent`.

Important:

```text
2.1% CH4 = 21000 ppm CH4
```

So send this:

```json
"ch4_ppm": 21000
```

not this:

```json
"ch4_ppm": 2.1
```

---

## LiDAR summary

Raw point cloud is not sent to backend. Adapter sends compact summary:

```json
{
  "min_distance": 0.4,
  "front_distance": 0.4,
  "left_distance": 0.8,
  "right_distance": 0.9,
  "ceiling_distance": 0.7,
  "floor_distance": 1.2,
  "obstacle_density": 0.6
}
```

---

## Mock Gazebo adapter

Run:

```bash
python adapters/gazebo_mock_adapter.py
```

It sends 7 simulated readings:

```text
x=12, z=2.5 → upper tunnel methane risk
x=20        → carbon monoxide risk
x=22        → oxygen drop + LiDAR obstacle warning
```

Then check:

```bash
curl http://127.0.0.1:8000/api/risk/current
curl http://127.0.0.1:8000/api/risk/trend
```