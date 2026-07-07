import urllib.request
import json
import os
from datetime import date, datetime, timezone, timedelta

from config.gazette_config import load_gazette_config
gazette_config = load_gazette_config()




class Scoreboard():
    def __init__(self):
        self.CACHE_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "cache"
        )
        self.cache_file  = os.path.join(self.CACHE_DIR, "scoreboard_cache.json")
        self.ENDPOINTS = gazette_config["score_endpoints"]
        self.TEAM_FILTERS = gazette_config["team_filters"]
        self.LEAGUE_ORDER = list(self.ENDPOINTS.keys())
        self.MAX_GAMES = 1000

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
        competitors = event.get("competitions", [{}])[0].get("competitors", [])
        abbrevs = [c.get("team", {}).get("abbreviation", "") for c in competitors]
        return any(f in abbrevs for f in filters)

    def isolate_opponent(self, game):
        print(game)
        #return [game["away_abbr"],game["home_abbr"]].remove(game["matched_team"])[0]
        return next(t for t in [game["away_abbr"], game["home_abbr"]] if t != game["matched_team"])
    
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
        if game_time_iso:
            gt = datetime.fromisoformat(game_time_iso.replace("Z", "+00:00"))
            # Convert UTC → Eastern for display (simple -4 offset; adjust if needed)
            gt_local    = gt - timedelta(hours=4)
            kickoff_str = gt_local.strftime("%A %-I:%M%p").lower().replace("am", "am").replace("pm", "pm")
            # Capitalise day name
            kickoff_str = kickoff_str[0].upper() + kickoff_str[1:]
        else:
            kickoff_str = ""

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

    def find_next_game(self, league, url, team_abbr):
        """
        Fetch the full schedule and return the next upcoming game opponent + time
        for a given team abbreviation. Falls back gracefully if unavailable.
        """
        try:
            data   = self.fetch(url)
            events = data.get("events", [])
            now    = datetime.now(timezone.utc)

            upcoming = []
            for event in events:
                date_str = event.get("date", "")
                if not date_str:
                    continue
                gt    = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                state = event.get("status", {}).get("type", {}).get("state", "pre")
                if gt > now and state == "pre":
                    competition = event.get("competitions", [{}])[0]
                    competitors = competition.get("competitors", [])
                    abbrevs     = [c.get("team", {}).get("abbreviation", "") for c in competitors]
                    if team_abbr in abbrevs:
                        opponent = next(
                            (c.get("team", {}).get("abbreviation", "?")
                             for c in competitors
                             if c.get("team", {}).get("abbreviation", "") != team_abbr),
                            "?"
                        )
                        gt_local   = gt - timedelta(hours=4)
                        time_str   = gt_local.strftime("%A %-I:%M%p")
                        time_str   = time_str[0].upper() + time_str[1:]
                        upcoming.append((gt, opponent, time_str))

            if upcoming:
                upcoming.sort(key=lambda x: x[0])
                _, opponent, time_str = upcoming[0]
                return opponent, time_str
        except Exception:
            pass
        return "", ""

    # ── Cache ─────────────────────────────────────────────────────

    def save_cache(self, games):
        payload = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "games":     games,
        }
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"  Scoreboard cached → {self.cache_file}")

    # ── Main ──────────────────────────────────────────────────────

    def main(self):
        all_games = []
        errors    = []
        #date_offset = -1
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
                    competitors = e.get("competitions", [{}])[0].get("competitors", [])
                    abbrevs = [c.get("team", {}).get("abbreviation", "") for c in competitors]
                    for f in filters:
                        if f in abbrevs:
                            matched_events.append((e, f))  # tuple of (event, matched_team)
                            break  # avoid duplicating if somehow both filters match

                events = matched_events

                if not events:
                    print("  No games in last 24hrs")
                    continue

                print(f"  {len(events)} game(s)")

                for event, matched_team in events[:self.MAX_GAMES]:
                    game = self.parse_game(event, league)
                    game["matched_team"] = matched_team
                    if game["state"] == "pre":
                        game = self.set_next_game_values(game)
                    all_games.append(game)
                    print(f"    {game['away_abbr']} {game['away_score']}  @  {game['home_abbr']} {game['home_score']}  [{game['detail']}]")

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

                # Look up next opponent using today's endpoint (pre-game events)
                today_str = date.today().strftime("%Y%m%d")
                url = f"{base_url}?dates={today_str}"
                opponent, next_time = self.find_next_game(league, url, team_abbr)

                # If today has nothing, try tomorrow
                if not opponent:
                    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y%m%d")
                    url = f"{base_url}?dates={tomorrow_str}"
                    opponent, next_time = self.find_next_game(league, url, team_abbr)

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