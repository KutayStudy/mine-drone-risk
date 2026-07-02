"""
Rule-based risk engine for the mine drone prototype.

Threshold TRIGGER POINTS are sourced (MSHA / OSHA / NIOSH - see
thresholds.py for citations). Score WEIGHTS, level cutoffs and the
0-100 scale are HEURISTIC/PROTOTYPE design choices.

Response contract kept from v0.1 (drone_id, source, timestamp, position,
gas, lidar, risk_score, risk_level, alarm_level, safety_status,
recommended_action, reasons, warnings, validation_errors) with three
additive fields: score_breakdown, unit_warnings, consistency_warnings.
"""

from typing import Dict, List, Optional
from backend.app.models.sensor import SensorReading
from backend.app.services import thresholds as T
from backend.app.services.trend_service import analyze_temporal_trend

W = T.SCORE_WEIGHTS

SAFETY_STATUS_PRIORITY = {
    "safe": 0,
    "caution_low_ceiling": 1,
    "caution_obstacle_nearby": 2,
    "unsafe_ceiling_distance": 3,
    "unsafe_obstacle_detected": 4,
}

def choose_higher_safety_status(current_status: str, candidate_status: str) -> str:
    current_priority = SAFETY_STATUS_PRIORITY.get(current_status, 0)
    candidate_priority = SAFETY_STATUS_PRIORITY.get(candidate_status, 0)

    if candidate_priority > current_priority:
        return candidate_status

    return current_status


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(value, maximum))

def validate_reading(reading: SensorReading) -> List[str]:
    """Hard validation. Any error -> measurement rejected."""
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


def detect_unit_warnings(reading: SensorReading) -> List[str]:
    """
    Soft plausibility checks for unit-confusion (HEURISTIC/PROTOTYPE).
    These do not reject the reading; they flag likely ppm/percent mix-ups.
    """
    warnings: List[str] = []
    gas = reading.gas

    if 0 < gas.ch4_ppm <= T.CH4_SUSPECT_PERCENT_INPUT_MAX:
        warnings.append(
            "ch4_ppm value is suspiciously low; it may be a percent value "
            "sent as ppm (1 % v/v = 10,000 ppm)"
        )

    if 0 < gas.o2_percent <= T.O2_SUSPECT_FRACTION_INPUT_MAX:
        warnings.append(
            "o2_percent value looks like a fraction (e.g. 0.209); expected "
            "percent (e.g. 20.9)"
        )

    if 0 <= gas.co2_ppm < T.CO2_ATMOSPHERIC_BACKGROUND_PPM:
        warnings.append(
            "co2_ppm is below atmospheric background (~400 ppm); possible "
            "unit error or uncalibrated sensor"
        )

    return warnings

def detect_consistency_warnings(reading: SensorReading) -> List[str]:
    """
    Cross-sensor physical consistency checks (HEURISTIC/PROTOTYPE).

    Displacement check: if O2 has dropped well below normal (20.9 %),
    *something* must occupy that volume. If reported CH4 + CO2 cannot
    account for the deficit, the O2 sensor and the gas sensors disagree.
    """
    warnings: List[str] = []
    gas = reading.gas

    o2_deficit_percent = T.O2_NORMAL_PERCENT - gas.o2_percent

    if o2_deficit_percent > T.O2_DISPLACEMENT_TOLERANCE:
        added_fraction = (gas.ch4_ppm + gas.co2_ppm) / 1_000_000.0
        explained_drop_percent = T.O2_NORMAL_PERCENT * added_fraction
        unexplained = o2_deficit_percent - explained_drop_percent

        if unexplained > T.O2_DISPLACEMENT_TOLERANCE:
            warnings.append(
                "O2 depression is larger than reported CH4/CO2 can explain; "
                "possible sensor inconsistency or an unmeasured gas"
            )

    return warnings

# ---------------------------------------------------------------------------
# Per-gas scoring (trigger points sourced; weights heuristic)
# ---------------------------------------------------------------------------

def _score_ch4(ch4_ppm: float, reasons: List[str]) -> float:
    if ch4_ppm >= T.CH4_LEL_PPM:
        reasons.append("CH4 at/above lower explosive limit (5 % v/v, LEL)")
        return W["ch4_at_lel"]

    if ch4_ppm >= T.CH4_MSHA_WITHDRAW_PPM:
        reasons.append("CH4 at/above MSHA withdrawal level (1.5 % v/v, 30 CFR 75.323)")
        return W["ch4_msha_withdraw"]

    if ch4_ppm >= T.CH4_MSHA_ACTION_PPM:
        reasons.append("CH4 at/above MSHA action level (1.0 % v/v, 30 CFR 75.323)")
        return W["ch4_msha_action"]

    if ch4_ppm >= T.CH4_10PCT_LEL_PPM:
        reasons.append("CH4 at/above 10 % of LEL (0.5 % v/v, confined-space alarm practice)")
        return W["ch4_10pct_lel"]

    return 0.0

def _score_co(co_ppm: float, reasons: List[str]) -> float:
    if co_ppm >= T.CO_IDLH_PPM:
        reasons.append("CO at/above NIOSH IDLH (1,200 ppm)")
        return W["co_idlh"]

    if co_ppm >= T.CO_NIOSH_CEILING_PPM:
        reasons.append("CO at/above NIOSH ceiling (200 ppm)")
        return W["co_ceiling"]

    if co_ppm >= T.CO_OSHA_PEL_TWA_PPM:
        reasons.append("CO at/above OSHA PEL 8-h TWA (50 ppm, exposure limit)")
        return W["co_osha_pel"]

    if co_ppm >= T.CO_NIOSH_REL_TWA_PPM:
        reasons.append("CO at/above NIOSH REL TWA (35 ppm, exposure limit)")
        return W["co_niosh_rel"]

    return 0.0

def _score_co2(co2_ppm: float, reasons: List[str]) -> float:
    if co2_ppm >= T.CO2_IDLH_PPM:
        reasons.append("CO2 at/above NIOSH IDLH (40,000 ppm / 4 % v/v)")
        return W["co2_idlh"]

    if co2_ppm >= T.CO2_MSHA_SHORT_TERM_PPM:
        reasons.append("CO2 at/above MSHA short-term / NIOSH STEL (30,000 ppm / 3 % v/v)")
        return W["co2_short_term"]

    if co2_ppm >= T.CO2_MSHA_MAX_PPM:
        reasons.append("CO2 at/above MSHA work-area max (0.5 % v/v, 30 CFR 75.321)")
        return W["co2_msha_max"]

    return 0.0

def _score_o2(o2_percent: float, reasons: List[str]) -> float:
    if o2_percent < T.O2_SEVERE_PERCENT:
        reasons.append("O2 below 16 % - severe deficiency (OSHA respiratory guidance)")
        return W["o2_severe"]

    if o2_percent < T.O2_MIN_SAFE_PERCENT:
        reasons.append("O2 below 19.5 % - oxygen-deficient (MSHA 30 CFR 75.321 / OSHA)")
        return W["o2_deficient"]

    return 0.0

# ---------------------------------------------------------------------------
# Main risk calculation
# ---------------------------------------------------------------------------

def calculate_risk_score(reading: SensorReading,recent_readings: Optional[List[SensorReading]] = None) -> Dict:
    """
    Compute the rule-based risk assessment for a single reading.
    If recent_readings, including this reading, is provided, a trend
    contribution is added via trend_service.
    """
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
            "validation_errors": validation_errors,
            "score_breakdown": None,
            "unit_warnings": detect_unit_warnings(reading),
            "consistency_warnings": [],
        }

    gas = reading.gas
    position = reading.position
    lidar = reading.lidar

    reasons: List[str] = []
    warnings: List[str] = []
    unit_warnings = detect_unit_warnings(reading)
    consistency_warnings = detect_consistency_warnings(reading)

    breakdown: Dict[str, float] = {
        "ch4_score": _score_ch4(gas.ch4_ppm, reasons),
        "co_score": _score_co(gas.co_ppm, reasons),
        "co2_score": _score_co2(gas.co2_ppm, reasons),
        "o2_score": _score_o2(gas.o2_percent, reasons),
        "combo_score": 0.0,
        "spatial_score": 0.0,
        "lidar_score": 0.0,
        "trend_score": 0.0,
    }

    if gas.o2_percent < T.O2_MIN_SAFE_PERCENT and gas.ch4_ppm >= T.CH4_MSHA_ACTION_PPM:
        breakdown["combo_score"] += W["o2_drop_with_ch4"]
        reasons.append("Oxygen deficiency combined with elevated methane")

    if position.z >= T.UPPER_VOLUME_Z_METERS and gas.ch4_ppm >= T.CH4_MSHA_ACTION_PPM:
        breakdown["spatial_score"] += W["ch4_upper_volume"]
        reasons.append("Methane accumulation risk in upper tunnel volume")

    safety_status = "safe"

    if lidar is not None:
        if lidar.min_distance < T.LIDAR_MIN_UNSAFE_M:
            breakdown["lidar_score"] += W["lidar_min_unsafe"]
            warnings.append("Obstacle dangerously close")
            safety_status = choose_higher_safety_status(safety_status,"unsafe_obstacle_detected")
        elif lidar.min_distance < T.LIDAR_MIN_CAUTION_M:
            breakdown["lidar_score"] += W["lidar_min_caution"]
            warnings.append("Nearby obstacle detected")
            safety_status = choose_higher_safety_status(safety_status,"caution_obstacle_nearby")

        if lidar.ceiling_distance < T.LIDAR_CEILING_UNSAFE_M:
            breakdown["lidar_score"] += W["lidar_ceiling_unsafe"]
            warnings.append("Ceiling too close")
            safety_status = choose_higher_safety_status(safety_status,"unsafe_ceiling_distance")
        elif lidar.ceiling_distance < T.LIDAR_CEILING_CAUTION_M:
            breakdown["lidar_score"] += W["lidar_ceiling_caution"]
            warnings.append("Low ceiling clearance")
            safety_status = choose_higher_safety_status(safety_status,"caution_low_ceiling")

    if recent_readings and len(recent_readings) >= 2:
        trend = analyze_temporal_trend(recent_readings)

        if trend.get("trend_available"):
            n_warnings = len(trend.get("trend_warnings", []))
            breakdown["trend_score"] = min(
                n_warnings * W["trend_per_warning"],
                W["trend_cap"])
            warnings.extend(trend["trend_warnings"])
            consistency_warnings.extend(trend.get("consistency_warnings", []))

    score = clamp(sum(breakdown.values()))

    if score >= T.RISK_LEVEL_CUTOFFS["critical"]:
        risk_level = "critical"
    elif score >= T.RISK_LEVEL_CUTOFFS["high"]:
        risk_level = "high"
    elif score >= T.RISK_LEVEL_CUTOFFS["medium"]:
        risk_level = "medium"
    else:
        risk_level = "low"

    alarm_level = determine_alarm_level(score, safety_status)

    recommended_action = decide_action(
        risk_level=risk_level,
        safety_status=safety_status,
        breakdown=breakdown,
        consistency_warnings=consistency_warnings,
    )

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
        "score_breakdown": breakdown,
        "unit_warnings": unit_warnings,
        "consistency_warnings": consistency_warnings,
    }


def determine_alarm_level(score: float, safety_status: str) -> str:
    """Alarm-level cutoffs are HEURISTIC/PROTOTYPE."""
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


def decide_action(risk_level: str,safety_status: str,breakdown: Optional[Dict[str, float]] = None,consistency_warnings: Optional[List[str]] = None,) -> str:
    """
    Map risk state to a mission-planner action. Priority order:
      1. critical gas risk        -> evacuate
      2. navigation unsafe        -> hold and alert operator
      3. high risk, roof methane  -> rescan the upper volume
      4. high risk                -> hold and alert operator
      5. medium risk, rising trend, or sensor inconsistency
                                  -> increase sampling frequency
      6. otherwise                -> continue monitoring
    """
    breakdown = breakdown or {}
    consistency_warnings = consistency_warnings or []

    if risk_level == "critical":
        return "trigger_alarm_and_evacuate_area"

    if safety_status.startswith("unsafe"):
        return "hold_position_and_alert_operator"

    if risk_level == "high":
        if breakdown.get("spatial_score", 0) > 0:
            return "rescan_upper_volume"
        return "hold_position_and_alert_operator"

    if risk_level == "medium":
        return "increase_sampling_frequency"

    if breakdown.get("trend_score", 0) > 0 or consistency_warnings:
        return "increase_sampling_frequency"

    return "continue_monitoring"


def get_current_risk(readings: List[SensorReading]) -> Optional[Dict]:
    if not readings:
        return None

    latest_reading = readings[-1]

    same_drone_readings = [
        reading for reading in readings
        if reading.drone_id == latest_reading.drone_id
    ]

    return calculate_risk_score(latest_reading,recent_readings=same_drone_readings)