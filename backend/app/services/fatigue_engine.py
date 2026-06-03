"""
Layer 1 — Physical Fatigue & Travel Decay
==========================================
Models the unique logistics burden of the 2026 tri-nation World Cup.
Hosted across USA, Canada, Mexico — 16 cities, 3 time zones, wildly
different climates (Miami heat vs Vancouver cold, Mexico City altitude).

Features produced:
  travel_decay_score  — cumulative km + timezone cross penalty (0–1, higher = more fatigued)
  rest_hours          — hours between last match and this kickoff
  rest_decay          — exponential penalty when rest < 96 hours
  climate_delta       — temperature / altitude mismatch penalty
  cumulative_fatigue  — compound decay across the tournament
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone


# ── WC 2026 Host Cities ────────────────────────────────────────────────────
# (city, lat, lon, timezone_offset_utc, altitude_m, avg_temp_june_celsius)
HOST_CITIES: Dict[str, Tuple[float, float, int, int, float]] = {
    "new_york":     (40.71,  -74.01, -4, 10,   24.0),
    "los_angeles":  (34.05, -118.24, -7, 71,   22.0),
    "dallas":       (32.78,  -96.80, -5, 139,  30.5),
    "san_francisco":(37.77, -122.42, -7, 16,   17.0),
    "miami":        (25.76,  -80.19, -4, 2,    32.0),
    "seattle":      (47.61, -122.33, -7, 56,   18.0),
    "boston":       (42.36,  -71.06, -4, 9,    21.0),
    "kansas_city":  (39.10,  -94.58, -5, 266,  27.0),
    "toronto":      (43.65,  -79.38, -4, 76,   22.0),
    "vancouver":    (49.25, -123.12, -7, 70,   18.0),
    "guadalajara":  (20.66, -103.35, -5, 1566, 26.0),  # altitude!
    "mexico_city":  (19.43,  -99.13, -5, 2240, 19.0),  # 2240m altitude
    "monterrey":    (25.67,  -100.31,-5, 538,  35.0),   # extreme heat
    "houston":      (29.76,   -95.37, -5,  32,   31.0),
}

# Which group plays where (simplified mapping for simulation)
CITY_SCHEDULE: Dict[str, List[str]] = {
    "BRA": ["miami", "los_angeles", "dallas"],
    "FRA": ["new_york", "boston", "toronto"],
    "ENG": ["new_york", "toronto", "boston"],
    "ARG": ["miami", "dallas", "los_angeles"],
    "ESP": ["los_angeles", "san_francisco", "seattle"],
    "POR": ["boston", "new_york", "toronto"],
    "GER": ["kansas_city", "dallas", "houston"],
    "NED": ["new_york", "boston", "toronto"],
    "BEL": ["toronto", "vancouver", "seattle"],
    "URU": ["miami", "dallas", "monterrey"],
    "CRO": ["los_angeles", "san_francisco", "seattle"],
    "ITA": ["new_york", "boston", "toronto"],
    "MAR": ["dallas", "miami", "monterrey"],
    "USA": ["kansas_city", "dallas", "miami"],
    "MEX": ["guadalajara", "mexico_city", "monterrey"],
    "COL": ["miami", "dallas", "monterrey"],
}

# Average inter-match travel distance for knockout rounds (km)
# Based on likely draw paths across the 3 countries
KO_TRAVEL_KM: Dict[str, float] = {
    "Round of 32":    1200.0,
    "Round of 16":    1800.0,
    "Quarter-finals": 2400.0,
    "Semi-finals":    2900.0,
    "Final":          1500.0,
}

# Timezone offsets for base country
TEAM_HOME_TZ: Dict[str, int] = {
    "BRA": -3, "FRA": 1,  "ENG": 0,  "ARG": -3, "ESP": 1,  "POR": 0,
    "GER": 1,  "NED": 1,  "BEL": 1,  "URU": -3, "CRO": 1,  "ITA": 1,
    "MAR": 0,  "USA": -5, "MEX": -6, "COL": -5,
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def compute_travel_decay(
    team_id: str,
    match_number: int,
    ko_round: Optional[str] = None,
    rest_hours: float = 120.0,
    players: Optional[List[Dict]] = None,
    apply_psychological_circadian: bool = False,
    hours_to_kickoff: float = 48.0,
) -> Dict[str, float]:
    """
    Compute the full physical fatigue state for a team before a given match.

    Args:
        team_id:      FIFA team ID (e.g. "BRA")
        match_number: 1-7 (group: 1-3, KO: 4-7)
        ko_round:     "Round of 32", "Round of 16", etc. (None for group stage)
        rest_hours:   Hours since last match kicked off

    Returns dict with:
        travel_decay_score  [0-1]  higher = more fatigued from travel
        rest_decay          [0-1]  higher = more fatigued from short rest
        altitude_penalty    [0-1]  higher = worse for high-altitude venues
        cumulative_fatigue  [0-1]  compound score across all factors
        travel_km           float  km traveled for this fixture
        timezone_shift      int    absolute hours of TZ shift
        rest_hours          float  rest hours (echoed back)
        sprint_speed_mult   float  multiplier on high-intensity sprinting
        defensive_recovery  float  multiplier on defensive recovery rate
    """
    cities = CITY_SCHEDULE.get(team_id, ["new_york", "dallas", "miami"])

    # Determine current and previous city
    if match_number <= 3:
        city_idx = min(match_number - 1, len(cities) - 1)
        prev_city_idx = max(0, city_idx - 1)
        curr_city = cities[city_idx]
        prev_city = cities[prev_city_idx]
        travel_km = 0.0 if match_number == 1 else _city_distance(prev_city, curr_city)
    else:
        # Knockout rounds — use average KO travel
        rname = ko_round or "Round of 32"
        travel_km = KO_TRAVEL_KM.get(rname, 1800.0)
        curr_city = cities[-1]  # Use last group city as proxy

    # Timezone shift from home country
    city_info = HOST_CITIES.get(curr_city, HOST_CITIES["new_york"])
    city_tz = city_info[2]
    home_tz = TEAM_HOME_TZ.get(team_id, 0)
    tz_shift = abs(city_tz - home_tz)

    # Travel decay: 0 at 0 km, saturates at ~5000 km
    travel_decay = 1.0 - math.exp(-travel_km / 3500.0)

    # Timezone shift decay: each hour of shift = 2.5% performance loss
    tz_decay = min(0.35, tz_shift * 0.025)

    # Rest decay: exponential penalty below 96 hours
    # No penalty above 120h; exponential below 96h
    if rest_hours >= 120:
        rest_decay = 0.0
    elif rest_hours >= 96:
        rest_decay = (120 - rest_hours) / 120 * 0.05
    else:
        # Exponential — at 72h rest: ~12%, at 48h: ~28%
        rest_decay = 0.05 + 0.25 * math.exp(-(rest_hours - 48) / 30)
        rest_decay = min(0.40, rest_decay)

    # Altitude penalty: Mexico City (2240m) and Guadalajara (1566m) hit fitness hard
    altitude_m = city_info[3]
    altitude_penalty = min(0.20, max(0.0, (altitude_m - 500) / 10000))

    # Climate stress (temperature extremes)
    city_temp = city_info[4]
    # Optimal playing temp ~18°C; both extremes penalise
    temp_stress = min(0.10, abs(city_temp - 18) / 200)

    # Cumulative fatigue: weighted combination
    cumulative = (
        travel_decay * 0.30 +
        tz_decay     * 0.25 +
        rest_decay   * 0.30 +
        altitude_penalty * 0.10 +
        temp_stress  * 0.05
    )
    cumulative = min(1.0, max(0.0, cumulative))

    # Physical performance multipliers
    sprint_speed_mult    = max(0.70, 1.0 - cumulative * 0.25)
    defensive_recovery   = max(0.72, 1.0 - cumulative * 0.22)

    result = {
        "travel_decay_score":  round(travel_decay, 4),
        "rest_decay":          round(rest_decay, 4),
        "altitude_penalty":    round(altitude_penalty, 4),
        "tz_shift_hours":      tz_shift,
        "cumulative_fatigue":  round(cumulative, 4),
        "travel_km":           round(travel_km, 1),
        "rest_hours":          rest_hours,
        "sprint_speed_mult":   round(sprint_speed_mult, 4),
        "defensive_recovery":  round(defensive_recovery, 4),
        "current_city":        curr_city,
    }

    if apply_psychological_circadian and players:
        from app.services.psychological_engine import (
            compute_squad_circadian,
            apply_circadian_to_fatigue,
        )
        circadian = compute_squad_circadian(players, rest_hours, cumulative, hours_to_kickoff)
        result = apply_circadian_to_fatigue(result, circadian)

    return result


def compute_fatigue_differential(
    team_a_id: str, team_b_id: str,
    match_number: int,
    ko_round: Optional[str] = None,
    rest_hours_a: float = 120.0,
    rest_hours_b: float = 120.0,
) -> float:
    """
    Returns a single differential fatigue feature for the feature vector.
    Positive = team_a is less fatigued than team_b (advantage).
    """
    fa = compute_travel_decay(team_a_id, match_number, ko_round, rest_hours_a)
    fb = compute_travel_decay(team_b_id, match_number, ko_round, rest_hours_b)
    # Differential: team_a advantage when its fatigue is lower
    return round(fb["cumulative_fatigue"] - fa["cumulative_fatigue"], 4)


def _city_distance(city_a: str, city_b: str) -> float:
    if city_a == city_b:
        return 0.0
    a = HOST_CITIES.get(city_a, HOST_CITIES["new_york"])
    b = HOST_CITIES.get(city_b, HOST_CITIES["new_york"])
    return haversine_km(a[0], a[1], b[0], b[1])
