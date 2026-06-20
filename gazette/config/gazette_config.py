from datetime import date, timedelta

gazette_config = {
    # ── Puller settings ───────────────────────────
    "feeds": {
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
        "sports": [
            "https://www.nytimes.com/athletic/rss/news/",
            # "https://www.hoopshype.com/",
        ],
        "tech": [
            "www.404media.co/rss",
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://blog.miguelgrinberg.com/feed",
            "http://feeds2.feedburner.com/thenextweb"
        ],
        "gaming": ["http://blog.us.playstation.com/tag/playstation-plus/feed/"],
        "products": ["http://blog.feedbin.me/atom.xml"],
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
        "local_news": [
            "transit",
            "SoHo",
            "Clinton Hill",
            "Fort Green",
            "Elementary School",
            "Rain",
            "Extreme Weather",
        ],
        "sports": ["Cleveland Cavaliers", "Lebron James", "NBA", "World Cup"],
        "tech": ["data engineering", "apple", "climate tech", "healthcare"],
        "gaming": ["PlayStation Plus Monthly Games"]
    },
    # ── File paths ────────────────────────────────
    "latest_output_file": "./cache/latest_rss_output.txt",  # the last file written by rss_puller.py
    "output_file": "./cache/rss_output.txt",  # written by rss_puller.py
    "summary_file": "rss_summary.txt",  # written by rss_summarizer.py
    # ── File paths ────────────────────────────────
    "recipient_name": "Scott"
}

gazette_config_production = {
    # ── Puller settings ───────────────────────────
    "feeds": {
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
        "sports": [
            "https://www.nytimes.com/athletic/rss/news/",
            # "https://www.hoopshype.com/",
        ],
        "tech": [
            "www.404media.co/rss",
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://blog.miguelgrinberg.com/feed",
            "http://feeds2.feedburner.com/thenextweb"
        ],
        "gaming": ["http://blog.us.playstation.com/tag/playstation-plus/feed/"],
        "products": ["http://blog.feedbin.me/atom.xml"],
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
        "local_news": [
            "transit",
            "SoHo",
            "Clinton Hill",
            "Fort Green",
            "Elementary School",
            "Rain",
            "Extreme Weather",
        ],
        "sports": ["Cleveland Cavaliers", "Lebron James", "NBA", "World Cup"],
        "tech": ["data engineering", "apple", "climate tech", "healthcare"],
        "gaming": ["PlayStation Plus Monthly Games"]
    },
    # ── File paths ────────────────────────────────
    "latest_output_file": "./cache/latest_rss_output.txt",  # the last file written by rss_puller.py
    "output_file": "./cache/rss_output.txt",  # written by rss_puller.py
    "summary_file": "rss_summary.txt",  # written by rss_summarizer.py
    # ── File paths ────────────────────────────────
    "recipient_name": "Scott"
}

