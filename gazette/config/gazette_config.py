import json
import os
from datetime import date, timedelta

_GAZETTE_ROOT = os.path.dirname(os.path.abspath(__file__))  # config/ dir
_PROJECT_ROOT = os.path.dirname(_GAZETTE_ROOT)  # gazette/ dir

CACHE_DIR = os.path.normpath(os.path.join(_PROJECT_ROOT, "cache"))


# ──Core settings ──────────────────────────────────────────────────
def _core_settings() -> dict:
    return {
        "start_date": (date.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "end_date": date.today().strftime("%Y-%m-%d"),
        "cache_dir": CACHE_DIR,
        "scoreboard_cache_file": os.path.join(CACHE_DIR, "scoreboard_cache.json"),
        "latest_rss_results": os.path.join(
            CACHE_DIR, "latest_rss_output.txt"
        ),  # the last file written by rss_puller.py
        "rss_results": os.path.join(
            CACHE_DIR, "rss_output.txt"
        ),  # written by rss_puller.py
        "rss_summary_file": os.path.join(CACHE_DIR, "rss_summary.json"),
    }


# Registry — GAZETTE_ENV value -> env var holding that environment's JSON config
configs = {
    "dev": "GAZETTE_CONFIG_DEV",
    "prod": "GAZETTE_CONFIG_PROD",
}


def _load_env_config(var_name: str) -> dict:
    raw = os.environ.get(var_name)
    if not raw:
        raise RuntimeError(
            f"Environment variable {var_name} is not set. "
            "It must contain this environment's config as a JSON object."
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"{var_name} is not valid JSON: {e}") from e
    if not isinstance(parsed, dict):
        raise ValueError(f"{var_name} must be a JSON object, got {type(parsed).__name__}")
    return parsed


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

    # JSON from the env var first, then Python-only values on top
    full_config = {**_load_env_config(configs[env]), **_core_settings()}

    active_topic_config = filter_inactive_topics(full_config)
    return active_topic_config