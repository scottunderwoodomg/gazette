import os
from datetime import date, timedelta

gazette_config_dev = {
    # ── Puller settings ───────────────────────────
    "active_topics": [],
    #"active_topics": ["tech"],
    "feeds": {
        "tech": ["http://feeds2.feedburner.com/thenextweb"],
    },
    "start_date": (date.today() - timedelta(days=1)).strftime(
        "%Y-%m-%d"
    ),  # Defaults to yesterday's date in YYYY-MM-DD format
    "end_date": date.today().strftime(
        "%Y-%m-%d"
    ),  # Defaults to today's date in YYYY-MM-DD format
    # ── Summarizer settings ───────────────────────
    "model": "claude-haiku-4-5-20251001",
    "interests": {
        "tech": ["AI"],
    },
    # ── Scoreboard Config ────────────────────────────────
    "score_endpoints": {
        "MLB":  "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    },
    "team_filters": {
        "MLB":  ["CLE"]
    },
    # ── File paths ────────────────────────────────
    "latest_output_file": "./cache/latest_rss_output.txt",  # the last file written by rss_puller.py
    "output_file": "./cache/rss_output.txt",  # written by rss_puller.py
    "summary_file": "rss_summary.txt",  # written by rss_summarizer.py
    # ── File paths ────────────────────────────────
    "recipient_name": "Scott",
}

gazette_config_prod = {
    # ── Puller settings ───────────────────────────
    "active_topics": ["local_news", "tech", "gaming", "products", "sports"],
    "feeds": {
        "world_news": [
            "https://reutersbest.com/feed/",
            "	http://feeds.reuters.com/reuters/topNews",
            "http://feeds.reuters.com/Reuters/worldNews",
        ],
        "local_news": [
            "https://gothamist.com/feed",
            "http://www.ny1.com/services/contentfeed.nyc%7Call-boroughs%7Cnews.landing.rss",
            "http://www.ny1.com/services/contentfeed.nyc%7Call-boroughs%7Cnews%7Ctransit.landing.rss",
            "http://www.ny1.com/services/contentfeed.nyc%7Call-boroughs%7Cnews%7Ceducation.landing.rss",
            "http://www.ny1.com/services/contentfeed.nyc%7Cbrooklyn.hero.rss",
            "http://www.ny1.com/services/contentfeed.nyc%7Call-boroughs%7Cweather%7Cweather-blogs.hero.rss"
            "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
            "https://nypost.com/feed/",
        ],
        "tech": [
            "www.404media.co/rss",
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://blog.miguelgrinberg.com/feed",
            "http://feeds2.feedburner.com/thenextweb",
        ],
        "gaming": ["http://blog.us.playstation.com/tag/playstation-plus/feed/"],
        "products": ["http://blog.feedbin.me/atom.xml"],
        "sports": [
            "https://www.nytimes.com/athletic/rss/news/",
            # "https://www.hoopshype.com/",
            "https://www.espn.com/espn/rss/nba/news",
            "https://api.foxsports.com/v2/content/optimized-rss?partnerKey=MB0Wehpmuj2lUhuRhQaafhBjAJqaPU244mlTDK1i&size=30&tags=fs/nba",
        ],
    },
    "start_date": (date.today() - timedelta(days=1)).strftime(
        "%Y-%m-%d"
    ),  # Defaults to yesterday's date in YYYY-MM-DD format
    "end_date": date.today().strftime(
        "%Y-%m-%d"
    ),  # Defaults to today's date in YYYY-MM-DD format
    # ── Summarizer settings ───────────────────────
    "model": "claude-haiku-4-5-20251001",
    # Interests filter: List any topics you care about. Only articles that are relevant to at least
    #   one of these interests will be included in the digest. Set to an empty list [] to include
    #   ALL articles regardless of topic.
    "interests": {
        "world_news": ["Top Stories"],
        "local_news": [
            "transit",
            "SoHo",
            "Clinton Hill",
            "Fort Green",
            "Elementary School",
            "Rain",
            "Extreme Weather",
        ],
        "tech": [
            "data engineering",
            "apple",
            "climate tech",
            "healthcare",
            "Arc Browser",
            "raindrop.io",
            "Express VPN",
            "Carrot Weather",
            "Notion",
        ],
        "gaming": ["PlayStation Plus Monthly Games"],
        "products": [],
        "sports": ["Cleveland Cavaliers", "Lebron James", "NBA", "World Cup"],
    },
    # ── Scoreboard Config ────────────────────────────────
    "score_endpoints": {
    "NBA":  "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    #"WNBA": "http://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
    #"NFL":  "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    #"CFB":  "http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
    #"NHL":  "http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    "MLB":  "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    #"MLS":  "http://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard",
    #"EPL":  "http://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
    "WC":   "http://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260611-20260719",
    },
    "team_filters": {
        "NBA":  ["CLE"],
        "MLB":  ["CLE"],
        "WC":   ["USA","ENG","FRA"],
    },
    # ── File paths ────────────────────────────────
    "latest_output_file": "./cache/latest_rss_output.txt",  # the last file written by rss_puller.py
    "output_file": "./cache/rss_output.txt",  # written by rss_puller.py
    "summary_file": "rss_summary.txt",  # written by rss_summarizer.py
    # ── File paths ────────────────────────────────
    "recipient_name": "Scott",
}


# Registry — used by the loader below
configs = {
    "dev": gazette_config_dev,
    "prod": gazette_config_prod,
}


def filter_inactive_topics(config: dict) -> dict:
    active_topics = config["active_topics"]
    topic_keys = ["interests", "feeds"]
    result = {}
    for name, child in config.items():
        if name in topic_keys:
            result[name] = {k: v for k, v in child.items() if k in active_topics}
        else:
            result[name] = child
    return result


def load_gazette_config():
    env = os.environ.get("GAZETTE_ENV", "dev")  # default to dev if unset
    if env not in configs:
        raise ValueError(
            f"Unknown GAZETTE_ENV '{env}'. Must be one of: {list(configs.keys())}"
        )
    print(f"[gazette] Loading config: {env}")

    active_topic_config = filter_inactive_topics(configs[env])
    return active_topic_config
