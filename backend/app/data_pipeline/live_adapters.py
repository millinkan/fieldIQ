"""
Phase 2 — Live Data Adapters
=============================
Pluggable adapters for free/low-tier live data APIs.
Each adapter implements the same DataAdapter interface so the
prediction engine doesn't care which source is active.

Supported providers:
  - API-Sports  (api-sports.io) — free tier: 100 req/day
  - Sportmonks  (sportmonks.com) — free tier: limited competitions
  - FootyStats  (footystats.org) — paid, higher volume
  - Mock        (no network, returns seed data — for offline dev)

Configure via .env:
  LIVE_DATA_PROVIDER=api_sports   # or: sportmonks | footystats | mock
  API_SPORTS_KEY=your_key
  SPORTMONKS_KEY=your_key
  FOOTYSTATS_API_KEY=your_key

Usage:
    from app.data_pipeline.live_adapters import get_adapter
    adapter = get_adapter()
    roster = await adapter.get_squad("BRA")
    fixtures = await adapter.get_fixtures(competition_id=1)
"""

import os
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# ── Rate limiting helpers ──────────────────────────────────────────────────

class RateLimiter:
    """Simple token-bucket rate limiter for API calls."""
    def __init__(self, calls_per_day: int):
        self.calls_per_day = calls_per_day
        self.calls_made = 0
        self.reset_date = datetime.now(timezone.utc).date()

    def can_call(self) -> bool:
        today = datetime.now(timezone.utc).date()
        if today != self.reset_date:
            self.calls_made = 0
            self.reset_date = today
        return self.calls_made < self.calls_per_day

    def record_call(self):
        self.calls_made += 1

    @property
    def remaining(self) -> int:
        return max(0, self.calls_per_day - self.calls_made)


# ── Base interface ─────────────────────────────────────────────────────────

class DataAdapter(ABC):
    """
    Every live data source implements this interface.
    Returns dicts compatible with FieldIQ's team/player schema.
    """
    provider_name: str = "base"

    @abstractmethod
    async def get_squad(self, team_id: str) -> Dict:
        """Return squad with player ratings, positions, injury status."""
        ...

    @abstractmethod
    async def get_fixtures(self, competition_id: int, season: Optional[int] = None) -> List[Dict]:
        """Return upcoming fixtures with team IDs and kickoff times."""
        ...

    @abstractmethod
    async def get_team_stats(self, team_id: str, season: Optional[int] = None) -> Dict:
        """Return team-level stats: xG, PPDA, form, etc."""
        ...

    @abstractmethod
    async def get_live_injuries(self, team_id: str) -> List[str]:
        """Return list of currently injured player IDs for a team."""
        ...

    def status(self) -> Dict:
        return {"provider": self.provider_name, "available": True}


# ── API-Sports adapter ─────────────────────────────────────────────────────

class APISportsAdapter(DataAdapter):
    """
    API-Sports (api-sports.io)
    Free tier: 100 requests/day, no credit card required.
    Sign up at https://api-sports.io

    Covers: 850+ leagues, lineups, injuries, live scores, standings.
    """
    provider_name = "api_sports"
    BASE = "https://v3.football.api-sports.io"

    # FIFA team ID → API-Sports team ID mapping (verified unique IDs)
    TEAM_MAP = {
        "BRA": 6,   "FRA": 2,   "ENG": 10,  "ARG": 26,
        "ESP": 9,   "POR": 27,  "GER": 25,  "NED": 11,
        "BEL": 1,   "URU": 15,  "CRO": 3,   "ITA": 13,
        "MAR": 31,  "USA": 528, "MEX": 16,  "COL": 21,
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.limiter = RateLimiter(calls_per_day=100)
        self.headers = {
            "x-apisports-key": api_key,
        }

    async def _get(self, endpoint: str, params: Dict = None) -> Dict:
        if not self.limiter.can_call():
            logger.warning(f"API-Sports rate limit reached ({self.limiter.calls_per_day}/day). "
                           "Returning empty response.")
            return {}
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{self.BASE}/{endpoint}",
                                 headers=self.headers, params=params or {})
            r.raise_for_status()
            self.limiter.record_call()
            logger.debug(f"API-Sports {endpoint} — {self.limiter.remaining} calls remaining today")
            return r.json()

    async def get_squad(self, team_id: str) -> Dict:
        api_id = self.TEAM_MAP.get(team_id)
        if not api_id:
            logger.warning(f"No API-Sports mapping for team {team_id}")
            return {}
        data = await self._get("players/squads", {"team": api_id})
        players = []
        for p in (data.get("response") or [{}])[0].get("players", []):
            players.append({
                "id":     f"{team_id}_{p['id']}",
                "name":   p.get("name", "Unknown"),
                "pos":    _map_position(p.get("position", "")),
                "rating": _estimate_rating(p),
                "pdv":    1.0,  # enriched by PDV service
                "age":    p.get("age", 26),
            })
        return {"team_id": team_id, "players": players, "source": "api_sports"}

    async def get_fixtures(self, competition_id: int, season: Optional[int] = None) -> List[Dict]:
        season = season or datetime.now(timezone.utc).year
        data = await self._get("fixtures", {"league": competition_id, "season": season, "next": 20})
        fixtures = []
        for f in (data.get("response") or []):
            fix = f.get("fixture", {})
            teams = f.get("teams", {})
            fixtures.append({
                "match_id":   fix.get("id"),
                "kickoff":    fix.get("date"),
                "status":     fix.get("status", {}).get("short"),
                "home_id":    teams.get("home", {}).get("id"),
                "home_name":  teams.get("home", {}).get("name"),
                "away_id":    teams.get("away", {}).get("id"),
                "away_name":  teams.get("away", {}).get("name"),
                "competition": competition_id,
            })
        return fixtures

    async def get_team_stats(self, team_id: str, season: Optional[int] = None) -> Dict:
        api_id = self.TEAM_MAP.get(team_id)
        if not api_id:
            return {}
        season = season or datetime.now(timezone.utc).year
        data = await self._get("teams/statistics", {"team": api_id, "season": season, "league": 1})
        resp = (data.get("response") or {})
        goals = resp.get("goals", {})
        return {
            "team_id":   team_id,
            "xg":        goals.get("for", {}).get("average", {}).get("total", 1.5),
            "xga":       goals.get("against", {}).get("average", {}).get("total", 1.2),
            "form":      _parse_form(resp.get("form", "")),
            "source":    "api_sports",
        }

    async def get_live_injuries(self, team_id: str) -> List[str]:
        api_id = self.TEAM_MAP.get(team_id)
        if not api_id:
            return []
        data = await self._get("injuries", {"team": api_id, "league": 1,
                                            "season": datetime.now(timezone.utc).year})
        return [
            f"{team_id}_{p['player']['id']}"
            for p in (data.get("response") or [])
            if p.get("player", {}).get("type", "").lower() in ("missing", "questionable")
        ]

    def status(self) -> Dict:
        return {
            "provider":     self.provider_name,
            "calls_today":  self.limiter.calls_made,
            "remaining":    self.limiter.remaining,
            "daily_limit":  self.limiter.calls_per_day,
            "available":    self.limiter.can_call(),
        }


# ── Sportmonks adapter ─────────────────────────────────────────────────────

class SportmonksAdapter(DataAdapter):
    """
    Sportmonks (sportmonks.com)
    Free tier: limited leagues, 180 req/hour.
    Sign up at https://sportmonks.com — free plan available.

    Strengths: deep squad data, injury feed, odds.
    """
    provider_name = "sportmonks"
    BASE = "https://api.sportmonks.com/v3/football"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.limiter = RateLimiter(calls_per_day=180 * 24)  # 180/hour
        self.params_base = {"api_token": api_key}

    async def _get(self, endpoint: str, params: Dict = None) -> Dict:
        if not self.limiter.can_call():
            logger.warning("Sportmonks rate limit reached.")
            return {}
        p = {**self.params_base, **(params or {})}
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{self.BASE}/{endpoint}", params=p)
            r.raise_for_status()
            self.limiter.record_call()
            return r.json()

    async def get_squad(self, team_id: str) -> Dict:
        data = await self._get(f"squads/teams/{team_id}", {"include": "players"})
        players = []
        for p in (data.get("data") or {}).get("players", []):
            info = p.get("player", p)
            players.append({
                "id":     str(info.get("id", "")),
                "name":   info.get("common_name", info.get("name", "Unknown")),
                "pos":    _map_position(info.get("position_id", "")),
                "rating": int(info.get("rating", 75) or 75),
                "pdv":    1.0,
            })
        return {"team_id": team_id, "players": players, "source": "sportmonks"}

    async def get_fixtures(self, competition_id: int, season: Optional[int] = None) -> List[Dict]:
        data = await self._get("fixtures/upcoming", {
            "filters": f"fixtureLeagues:{competition_id}", "include": "participants"
        })
        fixtures = []
        for f in (data.get("data") or [])[:20]:
            participants = {p["meta"]["location"]: p for p in f.get("participants", [])}
            fixtures.append({
                "match_id":  f.get("id"),
                "kickoff":   f.get("starting_at"),
                "home_id":   participants.get("home", {}).get("id"),
                "home_name": participants.get("home", {}).get("name"),
                "away_id":   participants.get("away", {}).get("id"),
                "away_name": participants.get("away", {}).get("name"),
            })
        return fixtures

    async def get_team_stats(self, team_id: str, season: Optional[int] = None) -> Dict:
        data = await self._get(f"statistics/seasons/teams/{team_id}")
        stats = (data.get("data") or [{}])[0]
        return {
            "team_id": team_id,
            "xg":   float(stats.get("xg", 1.5) or 1.5),
            "xga":  float(stats.get("xga", 1.2) or 1.2),
            "form": _parse_form(str(stats.get("form", ""))),
            "source": "sportmonks",
        }

    async def get_live_injuries(self, team_id: str) -> List[str]:
        data = await self._get("injuries", {"filters": f"injuryTeams:{team_id}"})
        return [str(p.get("player_id", "")) for p in (data.get("data") or [])]

    def status(self) -> Dict:
        return {
            "provider":   self.provider_name,
            "remaining":  self.limiter.remaining,
            "available":  self.limiter.can_call(),
        }


# ── FootyStats adapter (Phase 3 premium) ──────────────────────────────────

class FootyStatsAdapter(DataAdapter):
    """
    FootyStats (footystats.org)
    Paid plan required for full access.
    Use this once you have B2B contracts — richer xG, PPDA, deep completions.
    """
    provider_name = "footystats"
    BASE = "https://api.football-data-api.com"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _get(self, endpoint: str, params: Dict = None) -> Dict:
        p = {"key": self.api_key, **(params or {})}
        async with httpx.AsyncClient(timeout=20) as client:
            for attempt in range(3):
                try:
                    r = await client.get(f"{self.BASE}/{endpoint}", params=p)
                    r.raise_for_status()
                    return r.json()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        raise
        return {}

    async def get_squad(self, team_id: str) -> Dict:
        data = await self._get("team", {"team_name": team_id})
        players = []
        for p in (data.get("data") or {}).get("players", []):
            players.append({
                "id":     p.get("id", ""),
                "name":   p.get("name", ""),
                "pos":    _map_position(p.get("position", "")),
                "rating": int(p.get("rating", 75) or 75),
                "pdv":    1.0,
                "yellow_per90": float(p.get("yellow_cards_per_90_overall", 0.3) or 0.3),
                "reds_season":  int(p.get("red_cards_overall", 0) or 0),
            })
        return {"team_id": team_id, "players": players, "source": "footystats"}

    async def get_fixtures(self, competition_id: int, season: Optional[int] = None) -> List[Dict]:
        data = await self._get("league-matches", {"competition_id": competition_id, "max_per_page": 50})
        return [
            {
                "match_id":  m.get("id"),
                "kickoff":   m.get("date_unix"),
                "home_id":   m.get("homeID"),
                "home_name": m.get("home_name"),
                "away_id":   m.get("awayID"),
                "away_name": m.get("away_name"),
                "xg_home":   m.get("team_a_xg"),
                "xg_away":   m.get("team_b_xg"),
            }
            for m in (data.get("data") or [])
        ]

    async def get_team_stats(self, team_id: str, season: Optional[int] = None) -> Dict:
        data = await self._get("team-stats", {"team_id": team_id})
        stats = data.get("data") or {}
        return {
            "team_id":   team_id,
            "xg":        float(stats.get("xg_for_avg_overall", 1.5) or 1.5),
            "xga":       float(stats.get("xg_against_avg_overall", 1.2) or 1.2),
            "ppda":      float(stats.get("ppda", 10.5) or 10.5),
            "deep_comp": int(stats.get("deep_completions_per_game", 45) or 45),
            "shot_acc":  float(stats.get("shots_on_target_per_game", 4.5) or 4.5) / 15.0,
            "form":      _parse_form(str(stats.get("form", ""))),
            "source":    "footystats",
        }

    async def get_live_injuries(self, team_id: str) -> List[str]:
        data = await self._get("team-injuries", {"team_id": team_id})
        return [str(p.get("player_id", "")) for p in (data.get("data") or [])]


# ── Mock adapter (offline dev) ─────────────────────────────────────────────

class MockAdapter(DataAdapter):
    """
    Returns seed data — no network calls.
    Use for local development when you don't have API keys yet.
    """
    provider_name = "mock"

    async def get_squad(self, team_id: str) -> Dict:
        from app.data.seed_data import PLAYERS
        return {
            "team_id": team_id,
            "players": [p for p in PLAYERS if p["team_id"] == team_id],
            "source":  "mock",
        }

    async def get_fixtures(self, competition_id: int, season: Optional[int] = None) -> List[Dict]:
        return [
            {"match_id": 1, "kickoff": "2026-06-15T18:00:00Z",
             "home_id": "BRA", "home_name": "Brazil",
             "away_id": "FRA", "away_name": "France"},
            {"match_id": 2, "kickoff": "2026-06-15T21:00:00Z",
             "home_id": "ESP", "home_name": "Spain",
             "away_id": "ARG", "away_name": "Argentina"},
        ]

    async def get_team_stats(self, team_id: str, season: Optional[int] = None) -> Dict:
        from app.data.seed_data import TEAMS
        team = next((t for t in TEAMS if t["id"] == team_id), {})
        return {**team, "source": "mock"}

    async def get_live_injuries(self, team_id: str) -> List[str]:
        return []  # no injuries in mock mode


# ── Factory ────────────────────────────────────────────────────────────────

def get_adapter(provider: Optional[str] = None) -> DataAdapter:
    """
    Return the configured data adapter.
    Priority: env var LIVE_DATA_PROVIDER → argument → 'mock'

    .env configuration:
        LIVE_DATA_PROVIDER=api_sports
        API_SPORTS_KEY=your_key_here
        SPORTMONKS_KEY=your_key_here
        FOOTYSTATS_API_KEY=your_key_here
    """
    provider = provider or os.getenv("LIVE_DATA_PROVIDER", "mock")

    if provider == "api_sports":
        key = os.getenv("API_SPORTS_KEY", "")
        if not key:
            logger.warning("API_SPORTS_KEY not set — falling back to mock adapter")
            return MockAdapter()
        return APISportsAdapter(key)

    elif provider == "sportmonks":
        key = os.getenv("SPORTMONKS_KEY", "")
        if not key:
            logger.warning("SPORTMONKS_KEY not set — falling back to mock adapter")
            return MockAdapter()
        return SportmonksAdapter(key)

    elif provider == "footystats":
        key = os.getenv("FOOTYSTATS_API_KEY", "demo")
        if key == "demo":
            logger.warning("FOOTYSTATS_API_KEY is 'demo' — falling back to mock adapter")
            return MockAdapter()
        return FootyStatsAdapter(key)

    else:
        if provider != "mock":
            logger.warning(f"Unknown provider '{provider}' — using mock")
        return MockAdapter()


# ── Utility helpers ────────────────────────────────────────────────────────

def _map_position(raw: str) -> str:
    """Normalise position strings to FieldIQ position codes."""
    raw = str(raw).lower()
    if "goal" in raw or raw in ("1", "g"):           return "GK"
    if "centre-back" in raw or "cb" in raw:           return "CB"
    if "back" in raw or "defend" in raw:              return "FB"
    if "defensive mid" in raw or "cdm" in raw:        return "CDM"
    if "attacking mid" in raw or "cam" in raw:        return "CAM"
    if "midfield" in raw or "cm" in raw:              return "CM"
    if "wing" in raw or raw in ("rw", "lw"):          return "W"
    if "forward" in raw or "striker" in raw or "st" in raw: return "ST"
    return "CM"


def _estimate_rating(player_dict: Dict) -> int:
    """Estimate a 0-100 rating from API-Sports player data."""
    stats = player_dict.get("statistics", [{}])[0] if player_dict.get("statistics") else {}
    rating = stats.get("games", {}).get("rating")
    if rating:
        try:
            return min(99, max(60, round(float(rating) * 10)))
        except (ValueError, TypeError):
            pass
    return 75


def _parse_form(form_str: str) -> int:
    """Convert a form string like 'WDWWL' to a 0-100 form score."""
    if not form_str:
        return 60
    recent = form_str.upper().replace(" ", "")[-10:]  # last 10 results
    pts = sum(3 if r == "W" else 1 if r == "D" else 0 for r in recent)
    return min(100, round(pts / max(len(recent), 1) / 3 * 100))
