import urllib.request
import json
import os
from datetime import datetime, timezone, timedelta


ENDPOINTS = {
    "NBA":  "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    #"WNBA": "http://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
    #"NFL":  "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    #"CFB":  "http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
    #"NHL":  "http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    "MLB":  "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    #"MLS":  "http://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard",
    #"EPL":  "http://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
    "WC":   "http://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260611-20260719",
}

TEAM_FILTERS = {
    "NBA":  ["CLE"],
    "NFL":  [],
    "NHL":  [],
    "MLB":  ["CLE"],
    "WNBA": [],
    "CFB":  [],
    "MLS":  [],
    "EPL":  [],
    "WC":   [],
}

MAX_GAMES = 1000

LEAGUE_ORDER = list(ENDPOINTS.keys())


class Scoreboard():
    def __init__(self):
        self.script_dir  = "./cache/"
        self.cache_file  = os.path.join(self.script_dir, "scoreboard_cache.json")

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

        for league, url in ENDPOINTS.items():
            print(f"\n{'─'*50}")
            print(f"  {league}")
            print(f"{'─'*50}")

            try:
                data   = self.fetch(url)
                events = data.get("events", [])
            except Exception as e:
                print(f"  ERROR fetching {league}: {e}")
                errors.append((league, str(e)))
                continue

            filters = TEAM_FILTERS.get(league, [])
            events  = [e for e in events if self.within_24hrs(e) and self.team_matches(e, filters)]

            if not events:
                print("  No games in last 24hrs")
                continue

            print(f"  {len(events)} game(s)")

            for event in events[:MAX_GAMES]:
                game = self.parse_game(event, league)

                # For filtered teams, look up next opponent
                if filters:
                    for team_abbr in filters:
                        if team_abbr in (game["away_abbr"], game["home_abbr"]):
                            opponent, next_time = self.find_next_game(league, url, team_abbr)
                            game["next_opponent"]  = opponent
                            game["next_game_time"] = next_time

                all_games.append(game)
                print(f"    {game['away_abbr']} {game['away_score']}  @  {game['home_abbr']} {game['home_score']}  [{game['detail']}]")

        # Sort: by league order first, then game time within league
        def sort_key(g):
            league_idx = LEAGUE_ORDER.index(g["league"]) if g["league"] in LEAGUE_ORDER else 999
            return (league_idx, g["game_time_iso"])

        all_games.sort(key=sort_key)
        self.save_cache(all_games)

        if errors:
            print(f"\n{len(errors)} league(s) had errors:")
            for league, err in errors:
                print(f"  • {league}: {err}")


if __name__ == "__main__":
    sb = Scoreboard()
    sb.run_scoreboard()