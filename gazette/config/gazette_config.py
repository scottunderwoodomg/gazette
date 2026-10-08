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
    "thinking_status":"disabled",
    "effort": "medium",
    "filter_token_max": 4096,
    "summary_token_max": 2042,
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
    "recipient_name": "Friend",
}

gazette_config_prod = {
    # ── Puller settings ───────────────────────────
    "topics": {
        "tech": {
            "is_active": True,
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
    "thinking_status":"disabled",
    "effort": "medium",
    "filter_token_max": 4096,
    "summary_token_max": 2042,
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
    "recipient_name": "Friend",
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
