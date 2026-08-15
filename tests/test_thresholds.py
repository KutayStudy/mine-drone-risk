"""
Sanity checks for the sourced threshold ordering in
backend/app/services/thresholds.py.

These tests do not re-derive the regulatory values; they only assert
that the constants are internally consistent (e.g. an "action" level
is below a "withdraw" level, which is below the explosive limit).
"""
from backend.app.services import thresholds as T

def test_ch4_threshold_ordering():
    assert T.CH4_10PCT_LEL_PPM < T.CH4_MSHA_ACTION_PPM
    assert T.CH4_MSHA_ACTION_PPM < T.CH4_MSHA_WITHDRAW_PPM
    assert T.CH4_MSHA_WITHDRAW_PPM < T.CH4_MSHA_BLEEDER_MAX_PPM
    assert T.CH4_MSHA_BLEEDER_MAX_PPM < T.CH4_LEL_PPM

def test_co_threshold_ordering():
    assert T.CO_NIOSH_REL_TWA_PPM < T.CO_OSHA_PEL_TWA_PPM
    assert T.CO_OSHA_PEL_TWA_PPM < T.CO_NIOSH_CEILING_PPM
    assert T.CO_NIOSH_CEILING_PPM < T.CO_IDLH_PPM

def test_co2_threshold_ordering():
    assert T.CO2_MSHA_MAX_PPM < T.CO2_MSHA_SHORT_TERM_PPM
    assert T.CO2_MSHA_SHORT_TERM_PPM < T.CO2_IDLH_PPM

def test_o2_threshold_ordering():
    assert T.O2_SEVERE_PERCENT < T.O2_MIN_SAFE_PERCENT
    assert T.O2_MIN_SAFE_PERCENT < T.O2_NORMAL_PERCENT

def test_risk_level_cutoffs_ordering():
    cutoffs = T.RISK_LEVEL_CUTOFFS
    assert cutoffs["medium"] < cutoffs["high"] < cutoffs["critical"]

def test_lidar_unsafe_below_caution():
    assert T.LIDAR_MIN_UNSAFE_M < T.LIDAR_MIN_CAUTION_M
    assert T.LIDAR_CEILING_UNSAFE_M < T.LIDAR_CEILING_CAUTION_M

def test_score_weights_are_nonnegative():
    for name, weight in T.SCORE_WEIGHTS.items():
        assert weight >= 0, f"weight {name} is negative"

def test_ch4_lel_percent_conversion_matches_docstring():
    # 1 % v/v == 10,000 ppm, per the module docstring's unit convention.
    assert T.CH4_MSHA_ACTION_PPM == 10_000
    assert T.CH4_LEL_PPM == 50_000
