from typing import Literal, Optional
from pydantic import BaseModel
from backend.app.models.sensor import Position, IMUReading, LidarSummary

class DroneStatus(BaseModel):
    drone_id: str
    status: Literal["idle", "active", "returning", "error"]
    position: Position
    imu: Optional[IMUReading] = None
    lidar: Optional[LidarSummary] = None
    battery: Optional[float] = None