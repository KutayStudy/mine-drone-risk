"""
Gas safety thresholds for the mine drone risk prototype.

IMPORTANT DESIGN RULE
=====================
This module separates two very different kinds of numbers:

1. SOURCED SAFETY THRESHOLDS (regulatory / authoritative)
   Each constant carries the regulation or agency it comes from.
   These are *trigger points*, taken from MSHA / OSHA / NIOSH documents.

2. HEURISTIC PROTOTYPE COEFFICIENTS (our own design choices)
   Score weights, risk-level cutoffs and trend-rate limits have NO
   regulatory source. They are engineering heuristics for this prototype
   and are explicitly marked "HEURISTIC/PROTOTYPE".

This system is a research/decision-support prototype. It is NOT a
certified industrial gas safety system and must not be presented as one.

Unit conventions
================
- CH4, CO, CO2 are ppm (parts per million by volume).
- O2 is percent by volume.
- 1 % v/v == 10,000 ppm.  (e.g. 1.0 % CH4 == 10,000 ppm CH4)

Mine-safety thresholds (MSHA, 30 CFR Part 75 - underground coal mines)
vs. occupational exposure limits (OSHA PEL / NIOSH REL, workplace
time-weighted averages) are kept in separate blocks below and must not
be mixed up: MSHA values are mine-atmosphere action levels; PEL/REL
values are worker exposure limits over a shift.
"""

# ---------------------------------------------------------------------------
# 1) SOURCED SAFETY THRESHOLDS
# ---------------------------------------------------------------------------

# --- CH4 (methane) --- mine safety, MSHA 30 CFR 75.323 -----------------------
# https://www.ecfr.gov/current/title-30/chapter-I/subchapter-O/part-75/subpart-D/section-75.323
CH4_MSHA_ACTION_PPM = 10_000        # 1.0 % v/v: deenergize equipment, adjust
                                     # ventilation, stop work (75.323(b)(1))
CH4_MSHA_WITHDRAW_PPM = 15_000      # 1.5 % v/v: withdraw personnel, cut power
                                    # (75.323(b)(2))
CH4_MSHA_BLEEDER_MAX_PPM = 20_000   # 2.0 % v/v: max in bleeder/return splits
                                    # (75.323(e))
CH4_LEL_PPM = 50_000                # 5 % v/v: lower explosive limit of methane
                                    # (fire-science constant; explosive range
                                    # ~5-15 % v/v in air)
# 10 % of LEL is the standard confined-space "hazardous atmosphere" alarm
# practice (OSHA 1910.146 / 1915 Subpart B App A):
CH4_10PCT_LEL_PPM = 5_000           # 0.5 % v/v

# --- CO (carbon monoxide) --- occupational exposure + IDLH -------------------
# NIOSH Pocket Guide: https://www.cdc.gov/niosh/npg/npgd0105.html
# NIOSH IDLH doc:     https://www.cdc.gov/niosh/idlh/630080.html
# OSHA Table Z-1:     https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.1000TABLEZ1
CO_NIOSH_REL_TWA_PPM = 35           # NIOSH REL, full-shift TWA (exposure limit)
CO_OSHA_PEL_TWA_PPM = 50            # OSHA PEL, 8-hour TWA (exposure limit)
CO_NIOSH_CEILING_PPM = 200          # NIOSH ceiling - never exceed
CO_IDLH_PPM = 1_200                 # NIOSH IDLH - immediately dangerous

# --- CO2 (carbon dioxide) --- mine safety + occupational + IDLH --------------
# MSHA 30 CFR 75.321: https://www.law.cornell.edu/cfr/text/30/75.321
# NIOSH Pocket Guide: https://www.cdc.gov/niosh/npg/npgd0103.html
# NIOSH IDLH doc:     https://www.cdc.gov/niosh/idlh/124389.html
CO2_MSHA_MAX_PPM = 5_000            # 0.5 % v/v max where persons work/travel
                                    # (75.321(a)(1)); equals OSHA PEL /
                                    # NIOSH REL TWA of 5,000 ppm
CO2_MSHA_SHORT_TERM_PPM = 30_000    # 3.0 % v/v short-term limit in bleeder /
                                    # worked-out areas (75.321(a)(2)); equals
                                    # NIOSH STEL of 30,000 ppm
CO2_IDLH_PPM = 40_000               # 4 % v/v, NIOSH IDLH

# --- O2 (oxygen) --- mine safety + respiratory protection --------------------
# MSHA 30 CFR 75.321(a)(1): >= 19.5 % O2 where persons work or travel.
# OSHA 1910.134: < 19.5 % O2 is "oxygen-deficient" and generally treated
# as IDLH; 16-19.5 % causes symptoms under exertion.
# https://www.osha.gov/laws-regs/standardinterpretations/2007-04-02-0
O2_NORMAL_PERCENT = 20.9            # normal atmosphere
O2_MIN_SAFE_PERCENT = 19.5          # MSHA minimum / OSHA oxygen-deficiency line
O2_SEVERE_PERCENT = 16.0            # below ~16 %: rapid symptomatic impairment
                                    # (OSHA interpretation letter, 2007)

# ---------------------------------------------------------------------------
# 2) HEURISTIC / PROTOTYPE COEFFICIENTS  (no regulatory source)
# ---------------------------------------------------------------------------
# All numbers below are OUR prototype design choices. The trigger points
# they attach to are sourced above; the weights themselves are not.

SCORE_WEIGHTS = {  # HEURISTIC/PROTOTYPE
    # ch4_score
    "ch4_at_lel": 45,               # >= CH4_LEL_PPM (explosive range)
    "ch4_msha_withdraw": 30,        # >= CH4_MSHA_WITHDRAW_PPM
    "ch4_msha_action": 20,          # >= CH4_MSHA_ACTION_PPM
    "ch4_10pct_lel": 10,            # >= CH4_10PCT_LEL_PPM
    # co_score
    "co_idlh": 35,                  # >= CO_IDLH_PPM
    "co_ceiling": 25,               # >= CO_NIOSH_CEILING_PPM
    "co_osha_pel": 12,              # >= CO_OSHA_PEL_TWA_PPM
    "co_niosh_rel": 6,              # >= CO_NIOSH_REL_TWA_PPM
    # co2_score
    "co2_idlh": 25,                 # >= CO2_IDLH_PPM
    "co2_short_term": 18,           # >= CO2_MSHA_SHORT_TERM_PPM
    "co2_msha_max": 8,              # >= CO2_MSHA_MAX_PPM
    # o2_score
    "o2_severe": 35,                # < O2_SEVERE_PERCENT
    "o2_deficient": 20,             # < O2_MIN_SAFE_PERCENT
    # combo_score
    "o2_drop_with_ch4": 10,         # O2 deficient AND CH4 >= MSHA action level
    # spatial_score
    "ch4_upper_volume": 10,         # CH4 >= MSHA action level at z >= threshold
    # lidar_score (navigation safety, unrelated to gas regs)
    "lidar_min_unsafe": 20,
    "lidar_min_caution": 10,
    "lidar_ceiling_unsafe": 15,
    "lidar_ceiling_caution": 8,
    # trend_score
    "trend_per_warning": 5,         # per active trend warning
    "trend_cap": 15,                # max total trend contribution
}

# Risk-level cutoffs on the clamped 0-100 score.  HEURISTIC/PROTOTYPE.
RISK_LEVEL_CUTOFFS = {"critical": 80, "high": 50, "medium": 25}

# Spatial heuristic: CH4 is lighter than air and accumulates near the roof.
# (MSHA even requires methane tests >= 12 inches from the roof, 75.323(a).)
# The 2.0 m z-threshold itself is a prototype choice.  HEURISTIC/PROTOTYPE.
UPPER_VOLUME_Z_METERS = 2.0

# LiDAR clearance distances (meters).  HEURISTIC/PROTOTYPE (navigation).
LIDAR_MIN_UNSAFE_M = 0.5
LIDAR_MIN_CAUTION_M = 1.0
LIDAR_CEILING_UNSAFE_M = 0.5
LIDAR_CEILING_CAUTION_M = 1.0

# Trend change-rate limits (units per SECOND).  HEURISTIC/PROTOTYPE.
# There is no regulatory ppm/s rate limit; these are prototype leak-detection
# sensitivities chosen so that sustained rates would cross sourced thresholds
# within minutes (e.g. 100 ppm/s CH4 == 6,000 ppm/min -> MSHA action level
# reached from clean air in under 2 minutes).
TREND_RATE_LIMITS = {  # HEURISTIC/PROTOTYPE
    "ch4_ppm_per_second": 100.0,
    "co_ppm_per_second": 1.0,
    "co2_ppm_per_second": 50.0,
    "o2_percent_per_second": -0.02,   # falling faster than this warns
}
MIN_TREND_ELAPSED_SECONDS = 1.0       # ignore sub-second windows (noise)

# Unit / plausibility heuristics.  HEURISTIC/PROTOTYPE.
CH4_SUSPECT_PERCENT_INPUT_MAX = 5.0   # 0 < ch4_ppm <= 5 looks like % not ppm
O2_SUSPECT_FRACTION_INPUT_MAX = 1.0   # 0 < o2_percent <= 1 looks like fraction
CO2_ATMOSPHERIC_BACKGROUND_PPM = 400  # outdoor air ~400+ ppm; far below this
                                      # in a mine is physically implausible
O2_DISPLACEMENT_TOLERANCE = 0.5       # % O2 unexplained deficit tolerance