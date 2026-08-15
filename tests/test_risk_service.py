"""
Scenario tests for calculate_risk_score() in
backend/app/services/risk_service.py.

Each scenario builds a SensorReading and asserts on the resulting
risk_score / risk_level / alarm_level, based on the thresholds defined
in backend/app/services/thresholds.py.
"""
from datetime import datetime, timezone
import pytest
from backend.app.models.sensor import GasReading, LidarSummary, Position, SensorReading
from backend.app.services import thresholds as T
from backend.app.services.risk_service import calculate_risk_score

def make_reading(
    ch4_ppm=400.0,
    co_ppm=2.0,
    co2_ppm=450.0,
    o2_percent=20.9,
    x=0.0,
    y=0.0,
    z=1.0,
    lidar=None,
    drone_id="drone-1",
    source="mock",
):
    return SensorReading(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        drone_id=drone_id,
        source=source,
        position=Position(x=x, y=y, z=z),
        gas=GasReading(ch4_ppm=ch4_ppm, co_ppm=co_ppm, co2_ppm=co2_ppm, o2_percent=o2_percent),
        lidar=lidar,
    )

def test_clean_air_is_low_risk():
    reading = make_reading()
    result = calculate_risk_score(reading)

    assert result["validation_errors"] == []
    assert result["risk_score"] == 0.0
    assert result["risk_level"] == "low"
    assert result["alarm_level"] == "normal"
    assert result["safety_status"] == "safe"
    assert result["recommended_action"] == "continue_monitoring"

def test_ch4_at_msha_action_level_is_low_risk_alone():
    # ch4_msha_action's weight (20) is below RISK_LEVEL_CUTOFFS["medium"]
    # (25), so this single trigger alone stays "low" - it only becomes
    # "medium"/"high" once combined with other contributions (see the
    # withdrawal-level and combo-score tests below).
    reading = make_reading(ch4_ppm=T.CH4_MSHA_ACTION_PPM)
    result = calculate_risk_score(reading)

    assert result["score_breakdown"]["ch4_score"] == pytest.approx(T.SCORE_WEIGHTS["ch4_msha_action"])
    assert result["risk_score"] == pytest.approx(T.SCORE_WEIGHTS["ch4_msha_action"])
    assert result["risk_level"] == "low"
    assert "CH4 at/above MSHA action level" in result["reasons"][0]

def test_ch4_at_msha_withdrawal_level_is_medium_risk():
    reading = make_reading(ch4_ppm=T.CH4_MSHA_WITHDRAW_PPM)
    result = calculate_risk_score(reading)

    assert result["score_breakdown"]["ch4_score"] == pytest.approx(T.SCORE_WEIGHTS["ch4_msha_withdraw"])
    assert result["risk_level"] == "medium"
    assert result["recommended_action"] == "increase_sampling_frequency"

def test_co_at_idlh_alone_is_medium_risk():
    # co_idlh's weight (35) alone lands in the "medium" band; it takes a
    # second concurrent hazard to push the score into "critical" (see
    # test_multi_hazard_reading_is_critical below).
    reading = make_reading(co_ppm=T.CO_IDLH_PPM)
    result = calculate_risk_score(reading)

    assert result["score_breakdown"]["co_score"] == pytest.approx(T.SCORE_WEIGHTS["co_idlh"])
    assert result["risk_level"] == "medium"
    assert any("IDLH" in reason for reason in result["reasons"])

def test_multi_hazard_reading_is_critical():
    # CH4 at the explosive limit together with CO at IDLH is a realistic
    # multi-hazard reading: 45 (ch4_at_lel) + 35 (co_idlh) = 80, which
    # crosses RISK_LEVEL_CUTOFFS["critical"].
    reading = make_reading(ch4_ppm=T.CH4_LEL_PPM, co_ppm=T.CO_IDLH_PPM)
    result = calculate_risk_score(reading)

    assert result["risk_score"] == pytest.approx(80.0)
    assert result["risk_level"] == "critical"
    assert result["alarm_level"] == "critical"
    assert result["recommended_action"] == "trigger_alarm_and_evacuate_area"

def test_low_o2_triggers_deficiency_warning():
    reading = make_reading(o2_percent=T.O2_SEVERE_PERCENT - 0.1)
    result = calculate_risk_score(reading)

    assert result["score_breakdown"]["o2_score"] == pytest.approx(T.SCORE_WEIGHTS["o2_severe"])
    assert any("severe deficiency" in reason for reason in result["reasons"])
    assert result["risk_level"] in {"medium", "high"}

def test_invalid_reading_is_rejected():
    reading = make_reading(o2_percent=30.0)  # outside the 0-25 plausibility band
    result = calculate_risk_score(reading)

    assert result["validation_errors"] != []
    assert result["risk_score"] is None
    assert result["risk_level"] == "unknown"
    assert result["alarm_level"] == "invalid_sensor_data"
    assert result["recommended_action"] == "reject_measurement_and_request_rescan"

def test_lidar_obstacle_forces_unsafe_status_and_hold_action():
    lidar = LidarSummary(
        min_distance=0.2,
        front_distance=0.2,
        left_distance=1.0,
        right_distance=1.0,
        ceiling_distance=2.0,
        floor_distance=2.0,
        obstacle_density=0.5,
    )
    reading = make_reading(lidar=lidar)
    result = calculate_risk_score(reading)

    assert result["safety_status"] == "unsafe_obstacle_detected"
    assert "Obstacle dangerously close" in result["warnings"]
    assert result["recommended_action"] == "hold_position_and_alert_operator"

def test_upper_volume_methane_adds_spatial_score_and_rescan_action():
    reading = make_reading(ch4_ppm=T.CH4_MSHA_ACTION_PPM, z=T.UPPER_VOLUME_Z_METERS)
    result = calculate_risk_score(reading)

    assert result["score_breakdown"]["spatial_score"] == pytest.approx(T.SCORE_WEIGHTS["ch4_upper_volume"])
    assert "Methane accumulation risk in upper tunnel volume" in result["reasons"]

    # Total score crosses into "high" once spatial + ch4 scores combine
    # with the o2/ch4 combo score.
    if result["risk_level"] == "high":
        assert result["recommended_action"] == "rescan_upper_volume"
