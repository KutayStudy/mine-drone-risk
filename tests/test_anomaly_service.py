"""
Tests for backend/app/services/anomaly_service.py: the crossed_up /
crossed_down helpers, and the temporal-vs-spatial classification driven
by TEMPORAL_MAX_DISTANCE_M.
"""

from datetime import datetime, timedelta, timezone
from backend.app.models.sensor import GasReading, Position, SensorReading
from backend.app.services import anomaly_service as A

def test_crossed_up_true_when_value_rises_through_threshold():
    assert A.crossed_up(previous_value=5.0, current_value=15.0, threshold=10.0) is True

def test_crossed_up_false_when_already_above_threshold():
    assert A.crossed_up(previous_value=12.0, current_value=15.0, threshold=10.0) is False

def test_crossed_up_false_when_staying_below_threshold():
    assert A.crossed_up(previous_value=1.0, current_value=5.0, threshold=10.0) is False

def test_crossed_down_true_when_value_falls_through_threshold():
    assert A.crossed_down(previous_value=20.0, current_value=15.0, threshold=19.5) is True

def test_crossed_down_false_when_already_below_threshold():
    assert A.crossed_down(previous_value=15.0, current_value=10.0, threshold=19.5) is False

def make_reading(seconds_offset, x, y, z, ch4_ppm=400.0, source="mock", drone_id="drone-1"):
    return SensorReading(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds_offset),
        drone_id=drone_id,
        source=source,
        position=Position(x=x, y=y, z=z),
        gas=GasReading(ch4_ppm=ch4_ppm, co_ppm=2.0, co2_ppm=450.0, o2_percent=20.9),
    )

def test_classify_event_context_is_temporal_within_max_distance():
    previous = make_reading(0, x=0.0, y=0.0, z=0.0)
    current = make_reading(5, x=0.1, y=0.0, z=0.0)  # well under TEMPORAL_MAX_DISTANCE_M
    distance_m = A.distance_between(previous, current)
    assert distance_m <= A.TEMPORAL_MAX_DISTANCE_M
    assert A.classify_event_context(previous, current, distance_m) == "temporal_anomaly"

def test_classify_event_context_is_spatial_beyond_max_distance_new_cell():
    previous = make_reading(0, x=0.0, y=0.0, z=0.0)
    current = make_reading(5, x=10.0, y=0.0, z=0.0)  # beyond TEMPORAL_MAX_DISTANCE_M, new grid cell
    distance_m = A.distance_between(previous, current)

    assert distance_m > A.TEMPORAL_MAX_DISTANCE_M
    assert A.classify_event_context(previous, current, distance_m) == "spatial_gradient_alert"

def test_classify_event_context_esp32_pair_is_always_temporal():
    previous = make_reading(0, x=0.0, y=0.0, z=0.0, source="esp32")
    current = make_reading(5, x=50.0, y=0.0, z=0.0, source="esp32")
    distance_m = A.distance_between(previous, current)

    assert distance_m > A.TEMPORAL_MAX_DISTANCE_M
    assert A.classify_event_context(previous, current, distance_m) == "temporal_anomaly"

def test_detect_anomalies_empty_for_fewer_than_two_readings():
    assert A.detect_anomalies([]) == []
    assert A.detect_anomalies([make_reading(0, 0.0, 0.0, 0.0)]) == []

def test_detect_anomalies_flags_methane_threshold_crossing():
    from backend.app.services import thresholds as T

    previous = make_reading(0, x=0.0, y=0.0, z=1.0, ch4_ppm=1000.0)
    current = make_reading(10, x=0.2, y=0.0, z=1.0, ch4_ppm=T.CH4_MSHA_ACTION_PPM + 100)
    events = A.detect_anomalies([previous, current])
    assert any(event["type"] == "methane_action_threshold_crossed" for event in events)
