from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Position(BaseModel):
    x: float
    y: float
    z: float

class GasReading(BaseModel):
    ch4_ppm: float = Field(..., ge=0, description="Methane level in ppm")
    co_ppm: float = Field(..., ge=0, description="Carbon monoxide level in ppm")
    co2_ppm: float = Field(..., ge=0, description="Carbon dioxide level in ppm")
    o2_percent: float = Field(..., ge=0, le=100, description="Oxygen level in percentage")

class IMUReading(BaseModel):
    roll: float
    pitch: float
    yaw: float

class LidarSummary(BaseModel):
    min_distance: float = Field(..., ge=0)
    front_distance: float = Field(..., ge=0)
    left_distance: float = Field(..., ge=0)
    right_distance: float = Field(..., ge=0)
    ceiling_distance: float = Field(..., ge=0)
    floor_distance: float = Field(..., ge=0)
    obstacle_density: float = Field(..., ge=0, le=1)

class EnvironmentReading(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = Field(default=None, ge=0, le=100)
    pressure: Optional[float] = Field(default=None, ge=0)

class SensorReading(BaseModel):
    timestamp: datetime
    drone_id: str
    source: Literal["gazebo", "esp32", "mock"]
    position: Position
    gas: GasReading
    imu: Optional[IMUReading] = None
    lidar: Optional[LidarSummary] = None
    environment: Optional[EnvironmentReading] = None
    battery: Optional[float] = Field(default=None, ge=0, le=100)