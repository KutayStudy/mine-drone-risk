"""
Tests for backend/app/services/grid_service.py: cell-key rounding and
risk-zone detection against RISK_ZONE_MIN_SCORE.
"""
from datetime import datetime, timezone
from backend.app.models.sensor import GasReading, Position, SensorReading
from backend.app.services import grid_service as G
from backend.app.services import thresholds as T

def test_get_cell_key_rounds_down_to_cell_origin():
    position = Position(x=12.9, y=7.1, z=2.9)
    cell_key = G.get_cell_key(position)
    assert cell_key == (10.0, 5.0, 2.0)

def test_get_cell_key_on_exact_cell_boundary():
    position = Position(x=5.0, y=5.0, z=1.0)
    cell_key = G.get_cell_key(position)
    assert cell_key == (5.0, 5.0, 1.0)

def test_get_cell_key_handles_negative_coordinates():
    position = Position(x=-0.1, y=0.0, z=0.0)
    cell_key = G.get_cell_key(position)
    assert cell_key == (-5.0, 0.0, 0.0)

def test_format_cell_id_matches_cell_key():
    assert G.format_cell_id((10.0, 5.0, 2.0)) == "x10_y5_z2"

def make_reading(ch4_ppm, x, y, z, drone_id="drone-1"):
    return SensorReading(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        drone_id=drone_id,
        source="mock",
        position=Position(x=x, y=y, z=z),
        gas=GasReading(ch4_ppm=ch4_ppm, co_ppm=2.0, co2_ppm=450.0, o2_percent=20.9),
    )

def test_get_risk_zones_excludes_cells_below_min_score():
    clean_reading = make_reading(ch4_ppm=400.0, x=0.0, y=0.0, z=1.0)
    zones = G.get_risk_zones([clean_reading])
    assert zones == []

def test_get_risk_zones_includes_cells_at_or_above_min_score():
    # ch4_msha_withdraw scores 30, which is >= RISK_ZONE_MIN_SCORE (25).
    risky_reading = make_reading(ch4_ppm=T.CH4_MSHA_WITHDRAW_PPM, x=0.0, y=0.0, z=1.0)
    zones = G.get_risk_zones([risky_reading])
    assert len(zones) == 1
    assert zones[0]["risk_score"] >= G.RISK_ZONE_MIN_SCORE
    assert zones[0]["cell_id"] == G.format_cell_id(G.get_cell_key(risky_reading.position))

def test_build_3d_risk_map_groups_readings_into_same_cell():
    reading_a = make_reading(ch4_ppm=400.0, x=1.0, y=1.0, z=0.5)
    reading_b = make_reading(ch4_ppm=600.0, x=2.0, y=2.0, z=0.5)  # same 5x5x1 cell as reading_a

    risk_map = G.build_3d_risk_map([reading_a, reading_b])
    assert risk_map["cell_count"] == 1
    assert risk_map["cells"][0]["sample_count"] == 2
    assert risk_map["cells"][0]["gas_avg"]["ch4_ppm"] == 500.0
