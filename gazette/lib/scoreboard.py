import urllib.request
import json
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

# Optional: filter to specific teams per league (abbreviations). Empty list = show all.
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


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def within_24hrs(event):
    date_str = event.get("date")
    if not date_str:
        return False
    game_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    cutoff_front = datetime.now(timezone.utc) - timedelta(hours=24)
    cutoff_back = datetime.now(timezone.utc) + timedelta(hours=24)
    return cutoff_back > game_time >= cutoff_front


def team_matches(event, filters):
    if not filters:
        return True
    competitors = event.get("competitions", [{}])[0].get("competitors", [])
    abbrevs = [c.get("team", {}).get("abbreviation", "") for c in competitors]
    return any(f in abbrevs for f in filters)


def print_game(event, idx):
    competitors = event.get("competitions", [{}])[0].get("competitors", [])
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
    home = next((c for c in competitors if c.get("homeAway") == "home"), None)

    state  = event.get("status", {}).get("type", {}).get("state", "?")
    detail = event.get("status", {}).get("type", {}).get("detail", "?")
    tag    = {"pre": "🔜", "in": "🟢", "post": "✅"}.get(state, "❓")

    if away and home:
        a_name  = away.get("team", {}).get("abbreviation", "?")
        h_name  = home.get("team", {}).get("abbreviation", "?")
        a_score = away.get("score", "-")
        h_score = home.get("score", "-")
        matchup = f"{a_name} {a_score}  @  {h_name} {h_score}"
    else:
        matchup = event.get("name", "?")

    print(f"  {idx}. {tag} ({matchup} {detail})  |  {detail}")


def main():
    for league, url in ENDPOINTS.items():
        print(f"\n{'─'*50}")
        print(f"  {league}")
        print(f"{'─'*50}")
        data = fetch(url)
        events = data.get("events", [])

        filters = TEAM_FILTERS.get(league, [])
        events = [e for e in events if within_24hrs(e) and team_matches(e, filters)]

        if not events:
            print("  No games in last 24hrs")
            continue

        print(f"  {len(events)} game(s)")
        for i, event in enumerate(events[:MAX_GAMES], 1):
            print_game(event, i)


if __name__ == "__main__":
    main()
