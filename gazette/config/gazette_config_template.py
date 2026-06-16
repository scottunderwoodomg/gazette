from datetime import date, timedelta

gazette_config = {
    # ── Puller settings ───────────────────────────
    "feeds": {
        "topic_1": [
            "feed_link_1",
            "feed_link_2",
            "feed_link_3"
        ],
        "topic_2": [
            "feed_link_1"
        ],
    },
    "start_date": (date.today() - timedelta(days=1)).strftime(
        "%Y-%m-%d"
    ),  # Defaults to yesterday's date in YYYY-MM-DD format
    "end_date": date.today().strftime(
        "%Y-%m-%d"
    ),  # Defaults to today's date in YYYY-MM-DD format
    
    # ── Summarizer settings ───────────────────────
    "model": "model name",  # your claude model of choice, e.g. claude-haiku-4-5-20251001
    # Interests filter: List any topics you care about. Only articles that are relevant to at least 
    #   one of these interests will be included in the digest. Set to an empty list [] to include 
    #   ALL articles regardless of topic.
    "interests": {
        "topic_1": [
            "keyword_a",
            "keyword_b",
            "keyword_c",
        ],
        "topic_2": ["keyword_a"],
    },
    
    # ── File paths ────────────────────────────────
    "latest_output_file": f"./cache/latest_rss_output.txt",  # the last file written by rss_puller.py
    "output_file": f"./cache/rss_output.txt",  # written by rss_puller.py
    "summary_file": "rss_summary.txt",  # written by rss_summarizer.py
}
