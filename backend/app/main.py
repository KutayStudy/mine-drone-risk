from fastapi import FastAPI, Query, HTTPException
from backend.app.models.sensor import SensorReading
from backend.app.models.drone import DroneStatus
from backend.app.storage.memory_store import store
from backend.app.services.risk_service import get_current_risk
from backend.app.services.trend_service import analyze_temporal_trend
from backend.app.services.grid_service import build_3d_risk_map, get_risk_zones
from backend.app.services.anomaly_service import detect_anomalies

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

@app.get("/api/risk/current")
def get_risk_current():
    risk = get_current_risk(store.readings)
    if risk is None:
        return {"message": "no_readings_available","risk": None}
    return {"message": "risk_calculated","risk": risk}


@app.get("/api/risk/trend")
def get_risk_trend():
    trend = analyze_temporal_trend(store.readings)
    return {"message": "trend_analyzed","trend": trend}

@app.get("/api/risk/map3d")
def get_risk_map3d():
    risk_map = build_3d_risk_map(store.readings)
    return {"message": "map3d_generated","map": risk_map}

@app.get("/api/risk/zones")
def get_risk_zones_endpoint():
    zones = get_risk_zones(store.readings)
    return {"message": "risk_zones_detected","count": len(zones),"zones": zones}

@app.get("/api/anomalies")
def get_anomalies():
    anomalies = detect_anomalies(store.readings)
    return {"message": "anomalies_analyzed","count": len(anomalies),"anomalies": anomalies}