import logging
import re
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

from config.logging_config import setup_logging
setup_logging()

from lib.feed_summarizer import FeedSummarizer
from lib.gazette_email import GazetteEmail
from lib.rss_puller import RssPuller
from lib.scoreboard import Scoreboard

from config.gazette_config import load_gazette_config

gazette_config = load_gazette_config()
logger = logging.getLogger(__name__)

"""
Info goes here

Potential future improvements:
"""


class Gazette:
    def __init__(self):
        self.puller = RssPuller()
        self.summarizer = FeedSummarizer()
        self.scoreboard = Scoreboard()
        self.emailer = GazetteEmail()
        self.walkpath = os.path.dirname(os.path.abspath(__file__))

        self.latest_rss_pull_file = gazette_config["latest_rss_results"]
        self.rss_pull_file = gazette_config["rss_results"]

    def publish_gazette(self):
        """Pulls new articles, summarises target topics, and distributes via email."""
        self.puller.run_rss_puller()
        self.scoreboard.run_scoreboard()

        if self.check_for_news(self.rss_pull_file, self.latest_rss_pull_file):
            self.summarizer.run_feed_summarizer()
        else:
            logger.info("Nothing new in the news — skipping summariser.")

        self.emailer.run_gazette_email()

    def isolate_articles(self, content):
        """Strip all header/metadata lines, return only article entry lines."""
        lines = content.splitlines()
        clean = []
        for line in lines:
            stripped = line.strip()
            if (
                stripped.startswith("─")
                or stripped.startswith("FEED:")
                or stripped.startswith("Articles in range:")
                or stripped.startswith("No articles found")
            ):
                continue
            clean.append(line)
        text = "\n".join(clean)
        match = re.search(r"^\[\d+\]", text, re.MULTILINE)
        return text[match.start() :].strip() if match else text.strip()

    def check_for_news(self, fresh_file, latest_file):
        if not os.path.exists(fresh_file):
            logger.info(f"  No fresh RSS output at '{fresh_file}' — skipping summariser.")
            return False

        with open(fresh_file, "r", encoding="utf-8") as f:
            fresh_content = f.read()

        if os.path.exists(latest_file):
            with open(latest_file, "r", encoding="utf-8") as f:
                latest_content = f.read()
        else:
            latest_content = None

        fresh_articles  = self.isolate_articles(fresh_content)
        latest_articles = self.isolate_articles(latest_content) if latest_content else None

        is_dev  = os.environ.get("GAZETTE_ENV", "dev") == "dev"
        changed = fresh_articles != latest_articles

        # Prod + no change: nothing new to summarise.
        if not changed and not is_dev:
            logger.info("No change in articles since last run — skipping summariser.")
            return False

        # Promote the fresh pull so the summariser reads current content.
        shutil.copy2(fresh_file, latest_file)
        os.remove(fresh_file)

        if is_dev and not changed:
            logger.info("Dev mode: articles unchanged, summarising anyway.")
        else:
            logger.info(f"Articles changed — '{latest_file}' updated from fresh pull.")
        return True


if __name__ == "__main__":
    gazette = Gazette()
    gazette.publish_gazette()
