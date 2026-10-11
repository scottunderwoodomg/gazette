import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_ENV_JSON = "/app/env.json"


def load_env_json(path=None, required=True):
    """Load config from GAZETTE_CONFIG (JSON string) or a JSON file, then export to os.environ.

    Precedence:
      1. GAZETTE_CONFIG env var   (e.g. a Modal secret)
      2. path argument / ENV_JSON_PATH env var / /app/env.json   (e.g. docker -v mount)
    Existing environment variables are never overwritten.
    """
    raw = os.environ.get("GAZETTE_CONFIG")
    if raw:
        source = "GAZETTE_CONFIG env var"
    else:
        file_path = Path(path or os.environ.get("ENV_JSON_PATH", DEFAULT_ENV_JSON))
        if file_path.exists():
            raw = file_path.read_text()
            source = str(file_path)
        elif required:
            raise RuntimeError(
                f"No config found: set GAZETTE_CONFIG or provide a file at {file_path}"
            )
        else:
            logger.warning("No config found; continuing with empty config")
            return {}

    try:
        config = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Config from {source} is not valid JSON (line {e.lineno}, col {e.colno})") from None

    logger.info(f"Loaded config from {source}")

    for k, v in config.items():
        os.environ.setdefault(k, json.dumps(v) if isinstance(v, (dict, list)) else str(v))
    return config

