import os
from datetime import date, timedelta

_GAZETTE_ROOT = os.path.dirname(os.path.abspath(__file__))  # config/ dir
_PROJECT_ROOT = os.path.dirname(_GAZETTE_ROOT)  # gazette/ dir

CACHE_DIR = os.path.normpath(os.path.join(_PROJECT_ROOT, "cache"))

gazette_config_dev = {
    # ── Puller settings ───────────────────────────
    "topics": {
        "tech": {
            "is_active": False,
            "interests": ["AI"],
            "feeds": [
                "http://feeds2.feedburner.com/thenextweb",
            ],
        }
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
        "MLB": "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
        # "WC":   "http://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260611-20260719",
        "WC": "http://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard",
    },
    "team_filters": {
        "MLB": ["CLE"],
        "WC": ["USA", "ENG", "FRA"],
    },
    # ── File paths ────────────────────────────────
    "cache_dir": CACHE_DIR,
    "scoreboard_cache_file": os.path.join(CACHE_DIR, "scoreboard_cache.json"),
    "latest_rss_results": os.path.join(
        CACHE_DIR, "latest_rss_output.txt"
    ),  # the last file written by rss_puller.py
    "rss_results": os.path.join(
        CACHE_DIR, "rss_output.txt"
    ),  # written by rss_puller.py
    "rss_summary_file": os.path.join(CACHE_DIR, "rss_summary.json"),
    # ── File paths ────────────────────────────────
    "recipient_name": "Scott",
}

gazette_config_prod = {
    # ── Puller settings ───────────────────────────
    "topics": {
        "world_news": {
            "is_active": False,
            "interests": ["Top Stories"],
            "feeds": [
                "https://reutersbest.com/feed/",
                "	http://feeds.reuters.com/reuters/topNews",
                "http://feeds.reuters.com/Reuters/worldNews",
            ],
        },
        "local_news": {
            "is_active": True,
            "interests": [
                "transit",
                "SoHo",
                "Clinton Hill",
                "Fort Green",
                "Elementary School",
                "Rain",
                "Extreme Weather",
            ],
            "feeds": [
                "https://gothamist.com/feed",
                "http://www.ny1.com/services/contentfeed.nyc%7Call-boroughs%7Cnews.landing.rss",
                "http://www.ny1.com/services/contentfeed.nyc%7Call-boroughs%7Cnews%7Ctransit.landing.rss",
                "http://www.ny1.com/services/contentfeed.nyc%7Call-boroughs%7Cnews%7Ceducation.landing.rss",
                "http://www.ny1.com/services/contentfeed.nyc%7Cbrooklyn.hero.rss",
                "http://www.ny1.com/services/contentfeed.nyc%7Call-boroughs%7Cweather%7Cweather-blogs.hero.rss"
                "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
                "https://nypost.com/feed/",
            ],
        },
        "tech": {
            "is_active": True,
            "interests": [
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
            "feeds": [
                "www.404media.co/rss",
                "https://feeds.arstechnica.com/arstechnica/index",
                "https://blog.miguelgrinberg.com/feed",
                "http://feeds2.feedburner.com/thenextweb",
            ],
        },
        "gaming": {
            "is_active": True,
            "interests": ["PlayStation Plus Monthly Games"],
            "feeds": ["http://blog.us.playstation.com/tag/playstation-plus/feed/"],
        },
        "products": {
            "is_active": True,
            "interests": [],
            "feeds": ["http://blog.feedbin.me/atom.xml"],
        },
        "sports": {
            "is_active": True,
            "interests": ["Cleveland Cavaliers", "Lebron James", "NBA", "World Cup"],
            "feeds": [
                "https://www.nytimes.com/athletic/rss/news/",
                "https://www.espn.com/espn/rss/nba/news",
                "https://api.foxsports.com/v2/content/optimized-rss?partnerKey=MB0Wehpmuj2lUhuRhQaafhBjAJqaPU244mlTDK1i&size=30&tags=fs/nba",
            ],
        },
    },
    "start_date": (date.today() - timedelta(days=1)).strftime(
        "%Y-%m-%d"
    ),  # Defaults to yesterday's date in YYYY-MM-DD format
    "end_date": date.today().strftime(
        "%Y-%m-%d"
    ),  # Defaults to today's date in YYYY-MM-DD format
    # ── Summarizer settings ───────────────────────
    "model": "claude-haiku-4-5-20251001",
    # ── Scoreboard Config ────────────────────────────────
    "score_endpoints": {
        "NBA": "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
        # "WNBA": "http://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
        # "NFL":  "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
        # "CFB":  "http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
        # "NHL":  "http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
        "MLB": "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
        # "MLS":  "http://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard",
        # "EPL":  "http://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
        "WC": "http://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260611-20260719",
    },
    "team_filters": {
        "NBA": ["CLE"],
        "MLB": ["CLE"],
        "WC": ["USA", "ENG", "FRA"],
    },
    # ── File paths ────────────────────────────────
    "cache_dir": CACHE_DIR,
    "scoreboard_cache_file": os.path.join(CACHE_DIR, "scoreboard_cache.json"),
    "latest_rss_results": os.path.join(
        CACHE_DIR, "latest_rss_output.txt"
    ),  # the last file written by rss_puller.py
    "rss_results": os.path.join(
        CACHE_DIR, "rss_output.txt"
    ),  # written by rss_puller.py
    "rss_summary_file": os.path.join(CACHE_DIR, "rss_summary.json"),
    # ── File paths ────────────────────────────────
    "recipient_name": "Scott",
}


# Registry — used by the loader below
configs = {
    "dev": gazette_config_dev,
    "prod": gazette_config_prod,
}


def filter_inactive_topics(config: dict) -> dict:
    topics = config.get("topics", {})
    active_topic_names = [name for name, t in topics.items() if t.get("is_active")]

    result = dict(config)
    result["feeds"] = {name: topics[name]["feeds"] for name in active_topic_names}
    result["interests"] = {name: topics[name]["interests"] for name in active_topic_names}
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
