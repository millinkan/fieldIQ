"""
Layer 7 — Schedule Hardship & Travel Intelligence Engine
=========================================================
WC 2026 is played across 16 cities in 3 countries spanning 5 time zones.
No previous World Cup has had this level of internal travel variance.

Teams do not play in a single city — they move between venues with different:
  - Timezone offsets (up to 4hr variance within North America)
  - Temperatures (17°C Vancouver → 34°C Monterrey)
  - Altitudes (sea level → 2,240m Mexico City)
  - Flight distances (Vancouver → Miami = 4,200km)

The market prices teams as static entities. FieldIQ prices them as
organisms accumulating physical debt across matchdays.

Features produced:
  total_travel_km        — cumulative internal travel distance across group stage
  timezone_shifts        — total timezone changes across 3 matches
  temp_variance_c        — temperature range experienced across venues
  cumulative_hardship    — composite schedule difficulty score (0–1)
  hardship_class         — SEVERE / HIGH / MODERATE / LOW
  md3_penalty            — performance penalty specifically for matchday 3
                           (when fatigue compounds)
  vs_opponent_delta      — hardship differential vs specific opponent
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple

from app.services.climate_engine import VENUE_CLIMATE, FIXTURE_VENUE, TEAM_CLIMATE


# ── City coordinates and timezone offsets ─────────────────────────────────
CITY_DATA: Dict[str, Tuple[float, float, int]] = {
    # (lat, lon, utc_offset_june)
    "new_york":      (40.71,  -74.01, -4),
    "los_angeles":   (34.05, -118.24, -7),
    "dallas":        (32.78,  -96.80, -5),
    "san_francisco": (37.77, -122.42, -7),
    "miami":         (25.76,  -80.19, -4),
    "seattle":       (47.61, -122.33, -7),
    "boston":        (42.36,  -71.06, -4),
    "kansas_city":   (39.10,  -94.58, -5),
    "toronto":       (43.65,  -79.38, -4),
    "vancouver":     (49.25, -123.12, -7),
    "guadalajara":   (20.66, -103.35, -5),
    "mexico_city":   (19.43,  -99.13, -5),
    "monterrey":     (25.67, -100.31, -5),
    "atlanta":       (33.75,  -84.39, -4),
    "houston":       (29.76,  -95.37, -5),
    "philadelphia":  (39.95,  -75.17, -4),
}

# ── Team home timezone offsets (UTC) ──────────────────────────────────────
TEAM_HOME_TZ: Dict[str, int] = {
    "FRA": 2, "ESP": 2, "POR": 1, "ENG": 1, "BEL": 2, "NED": 2,
    "GER": 2, "CRO": 2, "SUI": 2, "AUT": 2, "SWE": 2, "SCO": 1,
    "NOR": 2, "CZE": 2, "BIH": 2, "TUR": 3,
    "BRA": -3, "ARG": -3, "COL": -5, "URU": -3, "ECU": -5,
    "PAR": -4, "CHI": -4,
    "MEX": -6, "USA": -5, "CAN": -5, "PAN": -5, "CUW": -4, "HAI": -5,
    "MAR": 1, "SEN": 0, "CIV": 0, "GHA": 0, "EGY": 2, "TUN": 1,
    "ALG": 1, "RSA": 2, "CPV": -1, "COD": 1,
    "JPN": 9, "KOR": 9, "AUS": 10, "NZL": 12, "IRN": 3.5,
    "SAU": 3, "IRQ": 3, "JOR": 3, "QAT": 3, "UZB": 5,
}


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def get_group_venues(group: str) -> List[str]:
    """Get the 3 venues (MD1, MD2, MD3) for a team in a given group."""
    # We need MD1, MD2, MD3 for this team specifically
    # For simplicity return all venues for the group (team plays at all 3)
    venues = []
    for md in ["MD1", "MD2", "MD3"]:
        fid = f"{group}-{md}-1"
        if fid in FIXTURE_VENUE:
            venues.append(FIXTURE_VENUE[fid])
        fid2 = f"{group}-{md}-2"
        if fid2 in FIXTURE_VENUE and len(venues) < 3:
            venues.append(FIXTURE_VENUE[fid2])
    return venues[:3]


# ── Pre-computed group venue sequences (home team perspective) ────────────
# Each group: [MD1_venue, MD2_venue, MD3_venue] for first-listed team
# (approximate — actual assignment depends on draw order)
GROUP_VENUE_SEQUENCE: Dict[str, List[str]] = {
    "A": ["mexico_city",   "atlanta",      "mexico_city"],
    "B": ["toronto",       "los_angeles",  "vancouver"],
    "C": ["new_york",      "boston",       "miami"],
    "D": ["los_angeles",   "seattle",      "los_angeles"],
    "E": ["houston",       "dallas",       "houston"],
    "F": ["dallas",        "kansas_city",  "houston"],
    "G": ["seattle",       "los_angeles",  "los_angeles"],
    "H": ["atlanta",       "atlanta",      "miami"],
    "I": ["new_york",      "philadelphia", "kansas_city"],
    "J": ["kansas_city",   "dallas",       "houston"],
    "K": ["houston",       "philadelphia", "boston"],
    "L": ["miami",         "atlanta",      "miami"],
}


def compute_schedule_hardship(
    team_id: str,
    group: str,
    matchday: Optional[int] = None,
) -> Dict:
    """
    Compute cumulative travel and climate hardship for a team across group stage.

    If matchday is specified, returns penalty specifically for that matchday
    (accounting for accumulated fatigue from prior matches).
    """
    team_tz = TEAM_HOME_TZ.get(team_id, 0)
    t_climate = TEAM_CLIMATE.get(team_id, {"heat_adapt": 0.5, "altitude_adapt": 0.3, "home_temp_c": 20})
    venues = GROUP_VENUE_SEQUENCE.get(group, ["new_york", "new_york", "new_york"])

    # Initial flight from home country to first venue
    first_venue = venues[0] if venues else "new_york"
    first_city = CITY_DATA.get(first_venue, CITY_DATA["new_york"])
    initial_tz_shift = abs(first_city[2] - team_tz)
    initial_km = _estimate_home_to_venue_km(team_id, first_venue)

    travel_segments = []
    cumulative_km = initial_km
    timezone_changes = initial_tz_shift
    temps = []
    altitudes = []

    for i, venue in enumerate(venues):
        v = VENUE_CLIMATE.get(venue, VENUE_CLIMATE["new_york"])
        c = CITY_DATA.get(venue, CITY_DATA["new_york"])
        temps.append(v[0])
        altitudes.append(v[2])

        if i > 0:
            prev_venue = venues[i-1]
            prev_city = CITY_DATA.get(prev_venue, CITY_DATA["new_york"])
            curr_city = c
            segment_km = haversine_km(
                prev_city[0], prev_city[1],
                curr_city[0], curr_city[1]
            )
            tz_change = abs(curr_city[2] - prev_city[2])
            cumulative_km += segment_km
            timezone_changes += tz_change
            travel_segments.append({
                "from": prev_venue, "to": venue,
                "km": round(segment_km, 0), "tz_change": tz_change
            })

    # ── Compute per-matchday penalties ────────────────────────────────────
    md_penalties = []
    for i, venue in enumerate(venues):
        v = VENUE_CLIMATE.get(venue, VENUE_CLIMATE["new_york"])
        temp_c, humidity, altitude_m, indoor_ac = v

        # Heat penalty
        if not indoor_ac:
            heat_stress = max(0, (temp_c - 18) / 17) * 0.6 + max(0, (humidity - 50) / 35) * 0.4
            heat_pen = heat_stress * (1.0 - t_climate["heat_adapt"]) * 0.12
        else:
            heat_pen = 0.0

        # Altitude penalty
        alt_pen = max(0, (altitude_m - 500) / 2500) * (1.0 - t_climate["altitude_adapt"]) * 0.15 if altitude_m > 500 else 0.0

        # Cumulative fatigue multiplier (each subsequent match costs more)
        fatigue_mult = 1.0 + i * 0.15  # MD1=1.0, MD2=1.15, MD3=1.30

        # Timezone shift penalty (especially severe for Asian/Oceanian teams)
        if i == 0:
            tz_pen = min(0.20, initial_tz_shift * 0.015)
        else:
            # Internal timezone shifts are smaller
            prev_tz = CITY_DATA.get(venues[i-1], CITY_DATA["new_york"])[2]
            curr_tz = CITY_DATA.get(venue, CITY_DATA["new_york"])[2]
            tz_pen = min(0.05, abs(curr_tz - prev_tz) * 0.015)

        matchday_penalty = (heat_pen + alt_pen + tz_pen) * fatigue_mult
        md_penalties.append(round(matchday_penalty, 4))

    total_penalty = sum(md_penalties)
    avg_penalty = total_penalty / 3 if md_penalties else 0

    # Temperature variance
    temp_range = max(temps) - min(temps) if temps else 0
    temp_shock_penalty = temp_range / 20 * 0.04

    # Final hardship score
    hardship_score = min(1.0, avg_penalty + temp_shock_penalty * 0.3 +
                         min(0.10, initial_tz_shift * 0.007))

    if hardship_score > 0.15:
        classification = "SEVERE"
    elif hardship_score > 0.09:
        classification = "HIGH"
    elif hardship_score > 0.05:
        classification = "MODERATE"
    else:
        classification = "LOW"

    result = {
        "team_id":               team_id,
        "group":                 group,
        "schedule_hardship":     round(hardship_score, 4),
        "hardship_class":        classification,
        "initial_tz_shift_hrs":  initial_tz_shift,
        "tz_shift":              initial_tz_shift,
        "total_travel_km":       round(cumulative_km, 0),
        "travel_km":             round(cumulative_km, 0),
        "timezone_changes":      timezone_changes,
        "venues":                venues,
        "avg_temp_c":            round(sum(temps) / max(1, len(temps)), 1),
        "temp_range_c":          round(temp_range, 1),
        "max_altitude_m":        max(altitudes) if altitudes else 0,
        "md1_penalty":           md_penalties[0] if len(md_penalties) > 0 else 0,
        "md2_penalty":           md_penalties[1] if len(md_penalties) > 1 else 0,
        "md3_penalty":           md_penalties[2] if len(md_penalties) > 2 else 0,
        "travel_segments":       travel_segments,
    }

    if matchday is not None and 1 <= matchday <= 3:
        result["requested_matchday_penalty"] = md_penalties[matchday - 1]

    return result


def compute_schedule_delta(
    home_id: str, away_id: str,
    group: str, matchday: int = 1,
) -> Dict:
    """
    Compute the schedule hardship differential between two teams.
    Positive = home team has easier schedule (competitive advantage).
    """
    h_sched = compute_schedule_hardship(home_id, group, matchday)
    a_sched = compute_schedule_hardship(away_id, group, matchday)

    delta = a_sched["schedule_hardship"] - h_sched["schedule_hardship"]
    md_delta = (
        a_sched.get(f"md{matchday}_penalty", 0) -
        h_sched.get(f"md{matchday}_penalty", 0)
    )

    if abs(delta) > 0.08:
        signal = "STRONG"
    elif abs(delta) > 0.04:
        signal = "MODERATE"
    else:
        signal = "WEAK"

    beneficiary = home_id if delta > 0 else away_id if delta < 0 else "neutral"

    return {
        "home_hardship":         h_sched["schedule_hardship"],
        "away_hardship":         a_sched["schedule_hardship"],
        "schedule_delta":        round(delta, 4),
        "matchday_delta":        round(md_delta, 4),
        "signal_strength":       signal,
        "beneficiary":           beneficiary,
        "home_tz_shift":         h_sched["initial_tz_shift_hrs"],
        "away_tz_shift":         a_sched["initial_tz_shift_hrs"],
        "home_travel_km":        h_sched["total_travel_km"],
        "away_travel_km":        a_sched["total_travel_km"],
        "home_hardship_class":   h_sched["hardship_class"],
        "away_hardship_class":   a_sched["hardship_class"],
    }


def _estimate_home_to_venue_km(team_id: str, venue: str) -> float:
    """Rough home-country to venue distance in km."""
    HOME_COORDS: Dict[str, Tuple[float, float]] = {
        "FRA": (48.85, 2.35), "ESP": (40.42, -3.70), "ENG": (51.51, -0.13),
        "GER": (52.52, 13.41), "NED": (52.37, 4.90), "BEL": (50.85, 4.35),
        "POR": (38.72, -9.14), "CRO": (45.81, 15.98), "SUI": (47.38, 8.54),
        "AUT": (48.21, 16.37), "SWE": (59.33, 18.07), "NOR": (59.91, 10.75),
        "SCO": (55.95, -3.19), "CZE": (50.08, 14.44), "BIH": (43.84, 18.36),
        "TUR": (39.93, 32.86),
        "BRA": (-15.78, -47.93), "ARG": (-34.60, -58.38), "COL": (4.71, -74.07),
        "URU": (-34.90, -56.19), "ECU": (-0.23, -78.52), "PAR": (-25.29, -57.65),
        "MEX": (19.43, -99.13), "USA": (38.89, -77.04), "CAN": (45.42, -75.69),
        "PAN": (8.99, -79.52), "CUW": (12.17, -68.93), "HAI": (18.54, -72.34),
        "MAR": (33.99, -6.85), "SEN": (14.69, -17.44), "CIV": (5.35, -4.00),
        "GHA": (5.56, -0.20), "EGY": (30.04, 31.24), "TUN": (36.82, 10.16),
        "ALG": (36.74, 3.06), "RSA": (-25.75, 28.19), "CPV": (14.93, -23.51),
        "COD": (-4.32, 15.32),
        "JPN": (35.68, 139.69), "KOR": (37.57, 126.98), "AUS": (-33.87, 151.21),
        "NZL": (-36.87, 174.77), "IRN": (35.69, 51.39), "SAU": (24.69, 46.72),
        "IRQ": (33.34, 44.40), "JOR": (31.95, 35.93), "QAT": (25.29, 51.53),
        "UZB": (41.30, 69.24),
    }

    home = HOME_COORDS.get(team_id)
    if not home:
        return 8000  # default intercontinental

    city = CITY_DATA.get(venue, CITY_DATA["new_york"])
    return haversine_km(home[0], home[1], city[0], city[1])
