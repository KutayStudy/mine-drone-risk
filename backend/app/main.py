from fastapi import FastAPI, Query, HTTPException
from backend.app.models.sensor import SensorReading
from backend.app.models.drone import DroneStatus
from backend.app.storage.memory_store import store

app = FastAPI(
    title="Mine Drone Risk Backend",
    description="Backend for 3D LiDAR-supported mine gas risk analysis prototype",
    version="0.1.0"
)

@app.get("/health")
def health_check():
    return {"status": "ok","service": "mine-drone-risk-backend"}

@app.post("/api/readings")
def add_reading(reading: SensorReading):
    saved = store.add_reading(reading)
    return {"message": "reading_saved","reading": saved,"total_readings": len(store.readings)}

@app.get("/api/readings")
def get_readings(limit: int = Query(default=100, ge=1, le=1000)):
    readings = store.get_readings(limit=limit)
    return {"count": len(readings),"readings": readings}

@app.get("/api/readings/{drone_id}")
def get_readings_by_drone(drone_id: str,limit: int = Query(default=100, ge=1, le=1000)):
    readings = store.get_readings_by_drone(drone_id=drone_id, limit=limit)
    return {"drone_id": drone_id,"count": len(readings),"readings": readings}

@app.post("/api/drone/status")
def update_drone_status(status: DroneStatus):
    saved = store.set_drone_status(status)
    return {"message": "drone_status_saved","status": saved}

@app.get("/api/drone/status/{drone_id}")
def get_drone_status(drone_id: str):
    status = store.get_drone_status(drone_id)

    if status is None:
        raise HTTPException(status_code=404, detail="Drone status not found")

    return {"status": status}


@app.get("/api/drones/statuses")
def get_all_drone_statuses():
    statuses = store.get_all_drone_statuses()

    return {"count": len(statuses),"statuses": statuses}