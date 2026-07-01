# API Contract

## Sources

- `gazebo`: simulated drone/platform
- `esp32`: hardware sensor box
- `mock`: synthetic test data

## Endpoints

### GET /health

Backend health check.

### POST /api/readings

Saves a sensor reading.

### GET /api/readings

Returns latest readings.

### GET /api/readings/{drone_id}

Returns latest readings for a specific drone.

### POST /api/drone/status

Updates current drone/platform status.

### GET /api/drone/status/{drone_id}

Returns current status for a specific drone.

### GET /api/drones/statuses

Returns current statuses for all drones.

## SensorReading Example

```json
{
  "timestamp": "2026-07-01T21:00:00",
  "drone_id": "drone-1",
  "source": "gazebo",
  "position": {"x": 12.4, "y": 5.1, "z": 1.8},
  "gas": {
    "ch4_ppm": 2.1,
    "co_ppm": 35,
    "co2_ppm": 800,
    "o2_percent": 19.4
  },
  "imu": {"roll": 0.1, "pitch": 0.2, "yaw": 1.5},
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

## DroneStatus Example

```json
{
  "drone_id": "drone-1",
  "status": "active",
  "position": {"x": 12.4, "y": 5.1, "z": 1.8},
  "imu": {"roll": 0.1, "pitch": 0.2, "yaw": 1.5},
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