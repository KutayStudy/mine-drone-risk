from typing import Dict, List, Optional
from backend.app.models.sensor import SensorReading
from backend.app.models.drone import DroneStatus

class MemoryStore:
    def __init__(self, max_readings: int = 1000) -> None:
        self.max_readings = max_readings
        self.readings: List[SensorReading] = []
        self.drone_statuses: Dict[str, DroneStatus] = {}

    def add_reading(self, reading: SensorReading) -> SensorReading:
        self.readings.append(reading)

        if len(self.readings) > self.max_readings:
            self.readings = self.readings[-self.max_readings:]

        return reading

    def get_readings(self, limit: int = 100) -> List[SensorReading]:
        if limit <= 0:
            return []

        return self.readings[-limit:]

    def get_latest_reading(self) -> Optional[SensorReading]:
        if not self.readings:
            return None

        return self.readings[-1]

    def get_readings_by_drone(self,drone_id: str,limit: int = 100,) -> List[SensorReading]:
        if limit <= 0:
            return []

        filtered = [reading for reading in self.readings if reading.drone_id == drone_id]
        return filtered[-limit:]

    def set_drone_status(self, status: DroneStatus) -> DroneStatus:
        self.drone_statuses[status.drone_id] = status
        return status

    def get_drone_status(self, drone_id: str) -> Optional[DroneStatus]:
        return self.drone_statuses.get(drone_id)

    def get_all_drone_statuses(self) -> List[DroneStatus]:
        return list(self.drone_statuses.values())

    def clear(self) -> None:
        self.readings.clear()
        self.drone_statuses.clear()

store = MemoryStore()