import urllib.request
import json
import os
from datetime import date, datetime, timezone, timedelta

from config.gazette_config import load_gazette_config
gazette_config = load_gazette_config()




class Scoreboard():
    def __init__(self):
        self.SCOREBOARD_CACHE_FILE = gazette_config["scoreboard_cache_file"]
        self.ENDPOINTS = gazette_config["score_endpoints"]
        self.TEAM_FILTERS = gazette_config["team_filters"]
        self.LEAGUE_ORDER = list(self.ENDPOINTS.keys())

    def run_scoreboard(self):
        self.main()

    # ── Fetch ─────────────────────────────────────────────────────

    def fetch(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())

    def within_24hrs(self, event):
        date_str = event.get("date")
        if not date_str:
            return False
        game_time    = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        cutoff_front = datetime.now(timezone.utc) - timedelta(hours=24)
        cutoff_back  = datetime.now(timezone.utc) + timedelta(hours=24)
        return cutoff_back > game_time >= cutoff_front

    def team_matches(self, event, filters):
        if not filters:
            return True
        return any(f in self.event_abbreviations(event) for f in filters)

    def isolate_opponent(self, game):
        return next(t for t in [game["away_abbr"], game["home_abbr"]] if t != game["matched_team"])
    
    def event_abbreviations(self, event):
        """Return the list of team abbreviations for both sides of an ESPN event."""
        competitors = event.get("competitions", [{}])[0].get("competitors", [])
        return [c.get("team", {}).get("abbreviation", "") for c in competitors]


    def set_next_game_values(self, game):
        game["next_game_time"] = game["kickoff"]
        game["next_opponent"] = self.isolate_opponent(game)
        return game

    # ── Parse ─────────────────────────────────────────────────────

    def parse_game(self, event, league):
        """Extract all fields needed by the email template from a raw ESPN event."""
        competition  = event.get("competitions", [{}])[0]
        competitors  = competition.get("competitors", [])

        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)

        state  = event.get("status", {}).get("type", {}).get("state", "pre")
        detail = event.get("status", {}).get("type", {}).get("detail", "")

        # Game time (ISO, UTC) — used for sorting
        game_time_iso = event.get("date", "")

        # Human-readable kickoff for display (e.g. "Tuesday 7:05pm")
        kickoff_str = self.format_kickoff(game_time_iso)

        game = {
            "league":       league,
            "game_time_iso": game_time_iso,   # for sorting
            "kickoff":      kickoff_str,       # for display
            "state":        state,             # pre / in / post
            "detail":       detail,            # "Final", "7:05 PM ET", "Q3 4:22", etc.
            "away_abbr":    "",
            "away_score":   "",
            "home_abbr":    "",
            "home_score":   "",
            "next_opponent": "",               # populated below for filtered teams
            "next_game_time": "",
            "matched_team":   ""
        }

        if away:
            game["away_abbr"]  = away.get("team", {}).get("abbreviation", "?")
            game["away_score"] = away.get("score", "-") if state != "pre" else ""
        if home:
            game["home_abbr"]  = home.get("team", {}).get("abbreviation", "?")
            game["home_score"] = home.get("score", "-") if state != "pre" else ""

        return game

    def format_kickoff(self, game_time_iso):
        """Human-readable Eastern-time kickoff string, e.g. 'Tuesday 7:05pm'."""
        if not game_time_iso:
            return ""
        gt = datetime.fromisoformat(game_time_iso.replace("Z", "+00:00"))
        gt_local = gt - timedelta(hours=4)  # TODO(7b): hardcoded EDT offset
        kickoff_str = gt_local.strftime("%A %-I:%M%p").lower()
        return kickoff_str[0].upper() + kickoff_str[1:]


    # ── Cache ─────────────────────────────────────────────────────

    def save_cache(self, games):
        payload = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "games":     games,
        }
        with open(self.SCOREBOARD_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"  Scoreboard cached → {self.SCOREBOARD_CACHE_FILE}")

    # ── Main ──────────────────────────────────────────────────────

    def main(self):
        all_games = []
        errors    = []
        date_offsets = [-1,0,1]

        for league, base_url in self.ENDPOINTS.items():
            for date_offset in date_offsets:
                date_str = (date.today() + timedelta(days=date_offset)).strftime("%Y%m%d")
                url = f"{base_url}?dates={date_str}"
                
                try:
                    data   = self.fetch(url)
                    events = data.get("events", [])
                except Exception as e:
                    print(f"  ERROR fetching {league} {date_str}: {e}")
                    errors.append((league, str(e)))
                    continue

                print(f"\n{'─'*50}")
                print(f"  {league} - {date_str}")
                print(f"{'─'*50}")

                filters = self.TEAM_FILTERS.get(league, [])
                matched_events = []
                for e in events:
                    if not self.within_24hrs(e):
                        continue
                    abbrevs = self.event_abbreviations(e)
                    for f in filters:
                        if f in abbrevs:
                            matched_events.append((e, f))
                            break

                events = matched_events

                if not events:
                    print("  No games in last 24hrs")
                    continue

                print(f"  {len(events)} game(s)")

                for event, matched_team in events:
                    game = self.parse_game(event, league)
                    game["matched_team"] = matched_team
                    if game["state"] == "pre":
                        game = self.set_next_game_values(game)
                    all_games.append(game)
                    print(f"    {game['away_abbr']} {game['away_score']}  @  {game['home_abbr']} {game['home_score']}  [{game['detail']}]")

        # ── Build a lookup of next-game info already fetched by the main loop ──
        # For each (league, team_abbr) that appears in an upcoming ("pre") game,
        # keep the earliest such game — set_next_game_values already computed
        # next_opponent/next_game_time for it during the initial fetch.
        upcoming_by_team = {}
        for g in all_games:
            if g["state"] != "pre":
                continue
            for team_abbr in (g["away_abbr"], g["home_abbr"]):
                key = (g["league"], team_abbr)
                existing = upcoming_by_team.get(key)
                if existing is None or g["game_time_iso"] < existing["game_time_iso"]:
                    upcoming_by_team[key] = g

            # ── Attach next game info to the most recent post/in game per filtered team ──
            for league, base_url in self.ENDPOINTS.items():
                filters = self.TEAM_FILTERS.get(league, [])
                if not filters:
                    continue

                for team_abbr in filters:
                    # Find the most recent completed/live game for this team in this league
                    team_games = [
                        g for g in all_games
                        if g["league"] == league
                        and g["state"] in ("post", "in")
                        and team_abbr in (g["away_abbr"], g["home_abbr"])
                    ]
                    if not team_games:
                        continue

                    # Sort by game time and take the most recent
                    team_games.sort(key=lambda g: g["game_time_iso"], reverse=True)
                    last_game = team_games[0]

                    # Reuse next-game info already fetched during the main loop
                    # (covers today/tomorrow via date_offsets), instead of re-fetching.
                    upcoming_game = upcoming_by_team.get((league, team_abbr))
                    if upcoming_game:
                        opponent  = self.isolate_opponent({**upcoming_game, "matched_team": team_abbr})
                        next_time = upcoming_game["kickoff"]
                    else:
                        opponent, next_time = "", ""

                    last_game["next_opponent"]  = opponent
                    last_game["next_game_time"] = next_time
                    print(f"  Next game for {team_abbr} ({league}): vs {opponent} {next_time}")

        # ── Remove pre-game cards for teams that already have a completed game ──
        covered_teams_by_league = {}
        for g in all_games:
            if g["state"] in ("post", "in"):
                covered_teams_by_league.setdefault(g["league"], set())
                covered_teams_by_league[g["league"]].add(g["away_abbr"])
                covered_teams_by_league[g["league"]].add(g["home_abbr"])

        all_games = [
            g for g in all_games
            if not (
                g["state"] == "pre"
                and g["away_abbr"] in covered_teams_by_league.get(g["league"], set())
                and g["home_abbr"] in covered_teams_by_league.get(g["league"], set())
            )
        ]

        # ── Sort and save ──────────────────────────────────────────────
        def sort_key(g):
            league_idx = self.LEAGUE_ORDER.index(g["league"]) if g["league"] in self.LEAGUE_ORDER else 999
            return (league_idx, g["game_time_iso"])

        all_games.sort(key=sort_key)
        self.save_cache(all_games)

        if errors:
            print(f"\n{len(errors)} league(s) had errors:")
            for league, err in errors:
                print(f"  • {url}\n    {err}")


if __name__ == "__main__":
    sb = Scoreboard()
    sb.run_scoreboard()