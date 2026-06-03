"""
Layer 5 — Psychological Context (Morale + Circadian Overlay)
=============================================================
Supplementary signals layered ON TOP of physical fatigue/rest/injury proxies.
Never replaces base fatigue_engine outputs.

A. Targeted abuse / morale — focus decay on pressure passing + penalties
B. Late-night activity — circadian compounding on cumulative_fatigue (capped)

Production path: NLP adapters on verified social accounts + incident triggers.
Demo path: seed signals in PLAYER_PSYCH_SIGNALS.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

# ── Demo psychological signals (replace with live NLP pipeline) ─────────────
PLAYER_PSYCH_SIGNALS: Dict[str, Dict] = {
    "vinicius": {
        "toxicity_baseline": 0.11,
        "toxicity_48h": 0.48,
        "recent_incident": "missed_penalty_vs_ARG",
        "incident_hours_ago": 36,
        "verified_account": True,
        "late_night_sessions": [
            {"hour_local": 1, "hours_before_kickoff": 30, "platform": "instagram"},
        ],
    },
    "casemiro": {
        "toxicity_baseline": 0.18,
        "toxicity_48h": 0.22,
        "recent_incident": None,
        "verified_account": True,
        "late_night_sessions": [],
    },
    "rodrygo": {
        "toxicity_baseline": 0.08,
        "toxicity_48h": 0.31,
        "recent_incident": "own_goal_qualifier",
        "incident_hours_ago": 52,
        "verified_account": True,
        "late_night_sessions": [
            {"hour_local": 0, "hours_before_kickoff": 18, "platform": "x"},
        ],
    },
    "endrick": {
        "toxicity_baseline": 0.05,
        "toxicity_48h": 0.06,
        "recent_incident": None,
        "verified_account": True,
        "late_night_sessions": [],
    },
    "paqueta": {
        "toxicity_baseline": 0.09,
        "toxicity_48h": 0.28,
        "recent_incident": "transfer_rumour_noise",
        "incident_hours_ago": 20,
        "verified_account": True,
        "late_night_sessions": [
            {"hour_local": 2, "hours_before_kickoff": 40, "platform": "twitch"},
        ],
    },
}

POSITION_FOCUS_WEIGHT = {
    "GK": 0.12, "CB": 0.10, "FB": 0.11, "CDM": 0.14,
    "CM": 0.16, "CAM": 0.18, "W": 0.17, "ST": 0.15,
}

TOXICITY_SPIKE_RATIO = 3.0
FOCUS_DECAY_MIN = 0.03
FOCUS_DECAY_MAX = 0.05
CIRCADIAN_MAX_UPLIFT = 0.08
MAX_CIRCADIAN_PLAYERS = 3
MIDNIGHT_HOUR = 0  # activity at hour >= 0 and < 6 counts as late-night


def _default_signal() -> Dict:
    return {
        "toxicity_baseline": 0.08,
        "toxicity_48h": 0.08,
        "recent_incident": None,
        "incident_hours_ago": None,
        "verified_account": False,
        "late_night_sessions": [],
    }


def get_player_psych_signal(player_id: str) -> Dict:
    return {**_default_signal(), **PLAYER_PSYCH_SIGNALS.get(player_id, {})}


def compute_player_morale(player_id: str) -> Dict:
    """
    A — Targeted abuse / morale vector.
    Requires sporting incident AND toxicity spike on verified account.
    """
    sig = get_player_psych_signal(player_id)
    baseline = max(sig["toxicity_baseline"], 0.01)
    ratio = sig["toxicity_48h"] / baseline
    has_incident = bool(sig.get("recent_incident"))
    incident_recent = (
        sig.get("incident_hours_ago") is not None
        and sig["incident_hours_ago"] <= 48
    )
    spike = ratio >= TOXICITY_SPIKE_RATIO
    active = bool(sig.get("verified_account") and has_incident and incident_recent and spike)

    if not active:
        return {
            "player_id": player_id,
            "active": False,
            "focus_decay": 0.0,
            "toxicity_ratio": round(ratio, 2),
            "triggers": [],
            "public_toxicity_index": round(sig["toxicity_48h"], 3),
        }

    severity = min(1.0, (ratio - TOXICITY_SPIKE_RATIO) / 2.0 + 0.5)
    focus_decay = FOCUS_DECAY_MIN + (FOCUS_DECAY_MAX - FOCUS_DECAY_MIN) * severity

    return {
        "player_id": player_id,
        "active": True,
        "focus_decay": round(focus_decay, 4),
        "toxicity_ratio": round(ratio, 2),
        "public_toxicity_index": round(sig["toxicity_48h"], 3),
        "recent_incident": sig["recent_incident"],
        "triggers": [
            f"incident:{sig['recent_incident']}",
            f"toxicity_spike:{ratio:.1f}x",
        ],
        "narrative": (
            f"Public toxicity spike ({ratio:.1f}x baseline) after "
            f"{sig['recent_incident']} — focus decay −{focus_decay*100:.1f}%"
        ),
    }


def compute_squad_morale(players: Optional[List[Dict]]) -> Dict:
    """Squad-level morale overlay for momentum / chemistry adjustments."""
    if not players:
        return {
            "squad_focus_penalty": 0.0,
            "flagged_players": [],
            "active_count": 0,
        }

    flagged = []
    weighted_sum = 0.0
    weight_total = 0.0

    for p in players:
        pid = p.get("id", "")
        morale = compute_player_morale(pid)
        if not morale["active"]:
            continue
        w = POSITION_FOCUS_WEIGHT.get(p.get("pos", "CM"), 0.12)
        weighted_sum += morale["focus_decay"] * w
        weight_total += w
        flagged.append({
            "player_id": pid,
            "name": p.get("name", pid),
            "focus_decay": morale["focus_decay"],
            "triggers": morale["triggers"],
        })

    penalty = round(weighted_sum / max(weight_total, 0.01), 4) if flagged else 0.0
    penalty = min(FOCUS_DECAY_MAX, penalty)

    return {
        "squad_focus_penalty": penalty,
        "flagged_players": flagged,
        "active_count": len(flagged),
    }


def compute_player_circadian(
    player_id: str,
    rest_hours: float,
    base_fatigue: float,
    hours_to_kickoff: float = 48.0,
) -> Dict:
    """
    B — Late-night activity circadian disruption (additive overlay only).
    Gated: verified late session + within pre-match window + elevated base load.
    """
    sig = get_player_psych_signal(player_id)
    if not sig.get("verified_account"):
        return {"player_id": player_id, "active": False, "disruption_score": 0.0, "triggers": []}

    sessions = [
        s for s in sig.get("late_night_sessions", [])
        if s.get("hours_before_kickoff", 999) <= hours_to_kickoff
        and s.get("hour_local", 12) < 6
    ]
    if not sessions:
        return {"player_id": player_id, "active": False, "disruption_score": 0.0, "triggers": []}

    elevated_load = base_fatigue >= 0.10 or rest_hours < 96
    if not elevated_load:
        # Minimal overlay when body is otherwise fresh
        return {
            "player_id": player_id,
            "active": True,
            "disruption_score": 0.02,
            "triggers": ["late_activity:minimal"],
            "sessions": sessions,
        }

    # Stronger penalty with more sessions and closer to kickoff
    score = 0.0
    for s in sessions:
        proximity = max(0.0, 1.0 - s["hours_before_kickoff"] / hours_to_kickoff)
        lateness = max(0.0, (6 - s.get("hour_local", 0)) / 6.0)
        score += 0.06 + proximity * 0.08 + lateness * 0.04

    score = min(0.25, score)
    return {
        "player_id": player_id,
        "active": True,
        "disruption_score": round(score, 4),
        "triggers": [f"late_activity:{s.get('platform', 'social')}" for s in sessions],
        "sessions": sessions,
    }


def compute_squad_circadian(
    players: Optional[List[Dict]],
    rest_hours: float,
    base_fatigue: float,
    hours_to_kickoff: float = 48.0,
) -> Dict:
    """Aggregate circadian disruption across XI (max 3 flagged starters)."""
    if not players:
        return {
            "squad_circadian_score": 0.0,
            "circadian_fatigue_uplift": 0.0,
            "flagged_players": [],
        }

    flagged = []
    for p in players:
        c = compute_player_circadian(
            p.get("id", ""), rest_hours, base_fatigue, hours_to_kickoff
        )
        if c["active"] and c["disruption_score"] > 0:
            flagged.append({**c, "name": p.get("name", p.get("id", "?")), "pos": p.get("pos", "?")})

    flagged.sort(key=lambda x: -x["disruption_score"])
    flagged = flagged[:MAX_CIRCADIAN_PLAYERS]

    if not flagged:
        return {
            "squad_circadian_score": 0.0,
            "circadian_fatigue_uplift": 0.0,
            "flagged_players": [],
        }

    squad_score = sum(f["disruption_score"] for f in flagged) / len(flagged)
    # Compounding multiplier on base fatigue — capped at +8%
    multiplier = min(CIRCADIAN_MAX_UPLIFT, squad_score * 0.35)
    uplift = round(base_fatigue * multiplier, 4)

    return {
        "squad_circadian_score": round(squad_score, 4),
        "circadian_fatigue_uplift": uplift,
        "circadian_multiplier": round(multiplier, 4),
        "flagged_players": flagged,
        "narrative": (
            f"{len(flagged)} starter(s) with late-night activity; "
            f"+{uplift:.3f} fatigue compounding on base {base_fatigue:.3f}"
        ),
    }


def apply_circadian_to_fatigue(fatigue: Dict[str, float], circadian: Dict) -> Dict[str, float]:
    """Apply circadian overlay — preserves base physical fatigue separately."""
    base = fatigue["cumulative_fatigue"]
    uplift = circadian.get("circadian_fatigue_uplift", 0.0)
    effective = min(1.0, base + uplift)

    out = dict(fatigue)
    out["base_cumulative_fatigue"] = round(base, 4)
    out["circadian_fatigue_uplift"] = round(uplift, 4)
    out["circadian_multiplier"] = circadian.get("circadian_multiplier", 0.0)
    out["squad_circadian_score"] = circadian.get("squad_circadian_score", 0.0)
    out["circadian_flagged_players"] = circadian.get("flagged_players", [])
    out["cumulative_fatigue"] = round(effective, 4)
    out["sprint_speed_mult"] = round(max(0.70, 1.0 - effective * 0.25), 4)
    out["defensive_recovery"] = round(max(0.72, 1.0 - effective * 0.22), 4)
    return out


def compute_team_psychological_profile(
    team_id: str,
    players: Optional[List[Dict]],
    rest_hours: float = 120.0,
    base_fatigue: float = 0.0,
    hours_to_kickoff: float = 48.0,
) -> Dict:
    """Full Layer 5 breakdown for API responses."""
    morale = compute_squad_morale(players)
    circadian = compute_squad_circadian(players, rest_hours, base_fatigue, hours_to_kickoff)
    return {
        "team_id": team_id,
        "layer": "psychological_context",
        "morale": morale,
        "circadian": circadian,
        "focus_decay_penalty_pct": round(morale["squad_focus_penalty"] * 100, 1),
        "circadian_uplift": circadian.get("circadian_fatigue_uplift", 0.0),
        "active_signals": morale["active_count"] + len(circadian.get("flagged_players", [])),
    }


def morale_pass_completion_factor(focus_penalty: float) -> float:
    """Scale pass-under-pressure capability (1.0 = no penalty)."""
    return max(0.90, 1.0 - focus_penalty)


def morale_penalty_factor(focus_penalty: float) -> float:
    """Scale penalty execution (1.0 = no penalty)."""
    return max(0.92, 1.0 - focus_penalty)
