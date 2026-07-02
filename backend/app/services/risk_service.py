from typing import Dict, List, Optional
from backend.app.models.sensor import SensorReading

def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(value, maximum))

def validate_reading(reading: SensorReading) -> List[str]:
    errors: List[str] = []
    gas = reading.gas
    lidar = reading.lidar

    if gas.ch4_ppm < 0:
        errors.append("Invalid CH4 value")
    if gas.co_ppm < 0:
        errors.append("Invalid CO value")
    if gas.co2_ppm < 0:
        errors.append("Invalid CO2 value")
    if not (0 <= gas.o2_percent <= 25):
        errors.append("Invalid O2 percentage")

    if lidar is not None:
        if lidar.min_distance < 0:
            errors.append("Invalid LiDAR min_distance")
        if lidar.ceiling_distance < 0:
            errors.append("Invalid LiDAR ceiling_distance")
        if lidar.obstacle_density < 0 or lidar.obstacle_density > 1:
            errors.append("Invalid LiDAR obstacle_density")
    return errors

def determine_alarm_level(score: float, safety_status: str) -> str:
    if safety_status.startswith("unsafe"):
        return "danger"
    if score >= 80:
        return "critical"
    if score >= 50:
        return "danger"
    if score >= 25:
        return "warning"
    if score >= 10:
        return "watch"
    return "normal"

def decide_action(risk_level: str, safety_status: str) -> str:
    if risk_level == "critical":
        return "trigger_alarm_and_evacuate_area"
    if safety_status.startswith("unsafe"):
        return "hold_position_and_notify_operator"
    if risk_level == "high":
        return "rescan_area_and_notify_operator"
    if risk_level == "medium":
        return "increase_sampling_frequency"
    return "continue_monitoring"

def calculate_risk_score(reading: SensorReading) -> Dict:
    validation_errors = validate_reading(reading)

    if validation_errors:
        return {
            "drone_id": reading.drone_id,
            "source": reading.source,
            "timestamp": reading.timestamp,
            "position": reading.position,
            "gas": reading.gas,
            "lidar": reading.lidar,
            "risk_score": None,
            "risk_level": "unknown",
            "alarm_level": "invalid_sensor_data",
            "safety_status": "invalid_sensor_data",
            "recommended_action": "reject_measurement_and_request_rescan",
            "reasons": [],
            "warnings": [],
            "validation_errors": validation_errors}

    gas = reading.gas
    position = reading.position
    lidar = reading.lidar

    score = 0.0
    reasons: List[str] = []
    warnings: List[str] = []

    if gas.ch4_ppm >= 50000:
        score += 45
        reasons.append("Critical methane level")
    elif gas.ch4_ppm >= 20000:
        score += 25
        reasons.append("High methane level")
    elif gas.ch4_ppm >= 10000:
        score += 10
        reasons.append("Elevated methane level")

    if gas.co_ppm >= 100:
        score += 35
        reasons.append("Critical carbon monoxide level")
    elif gas.co_ppm >= 50:
        score += 20
        reasons.append("High carbon monoxide level")
    elif gas.co_ppm >= 25:
        score += 10
        reasons.append("Elevated carbon monoxide level")

    if gas.co2_ppm >= 10000:
        score += 20
        reasons.append("High carbon dioxide level")
    elif gas.co2_ppm >= 5000:
        score += 10
        reasons.append("Elevated carbon dioxide level")

    if gas.o2_percent <= 18.0:
        score += 30
        reasons.append("Critical oxygen drop")
    elif gas.o2_percent <= 19.5:
        score += 15
        reasons.append("Low oxygen level")

    if gas.o2_percent <= 19.5 and gas.ch4_ppm >= 10000:
        score += 15
        reasons.append("Oxygen drop combined with methane increase")

    if position.z >= 2.0 and gas.ch4_ppm >= 20000:
        score += 15
        reasons.append("Methane accumulation risk in upper tunnel volume")

    safety_status = "safe"

    if lidar is not None:
        if lidar.min_distance < 0.5:
            score += 20
            warnings.append("Obstacle dangerously close")
            safety_status = "unsafe_obstacle_detected"
        elif lidar.min_distance < 1.0:
            score += 10
            warnings.append("Nearby obstacle detected")
            safety_status = "caution_obstacle_nearby"

        if lidar.ceiling_distance < 0.5:
            score += 15
            warnings.append("Ceiling too close")
            safety_status = "unsafe_ceiling_distance"
        elif lidar.ceiling_distance < 1.0:
            score += 8
            warnings.append("Low ceiling clearance")
            if safety_status == "safe":
                safety_status = "caution_low_ceiling"

    score = clamp(score)

    if score >= 80:
        risk_level = "critical"
    elif score >= 50:
        risk_level = "high"
    elif score >= 25:
        risk_level = "medium"
    else:
        risk_level = "low"

    alarm_level = determine_alarm_level(score, safety_status)
    recommended_action = decide_action(risk_level, safety_status)

    return {
        "drone_id": reading.drone_id,
        "source": reading.source,
        "timestamp": reading.timestamp,
        "position": reading.position,
        "gas": reading.gas,
        "lidar": reading.lidar,
        "risk_score": score,
        "risk_level": risk_level,
        "alarm_level": alarm_level,
        "safety_status": safety_status,
        "recommended_action": recommended_action,
        "reasons": reasons,
        "warnings": warnings,
        "validation_errors": validation_errors,
    }


def get_current_risk(readings: List[SensorReading]) -> Optional[Dict]:
    if not readings:
        return None

    latest_reading = readings[-1]
    return calculate_risk_score(latest_reading)