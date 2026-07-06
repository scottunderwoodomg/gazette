import re
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

from lib.feed_summarizer import FeedSummarizer
from lib.gazette_email import GazetteEmail
from lib.rss_puller import RssPuller
from lib.scoreboard import Scoreboard

from config.gazette_config import load_gazette_config

gazette_config = load_gazette_config()

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

        self.latest_rss_pull_file = gazette_config["latest_output_file"]
        self.rss_pull_file = gazette_config["output_file"]

    def publish_gazette(self):
        """Pulls new articles, summarises target topics, and distributes via email."""
        self.puller.run_rss_puller()
        self.scoreboard.run_scoreboard()

        if self.check_for_news(self.rss_pull_file, self.latest_rss_pull_file):
            self.summarizer.run_feed_summarizer()
        else:
            print("Nothing new in the news — skipping summariser.")

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

    def check_for_news(self, file_a, file_b):
        with open(file_a, "r", encoding="utf-8") as f:
            content_a = f.read()
            print(len(content_a))

        if os.path.exists(file_b):
            with open(file_b, "r", encoding="utf-8") as f:
                content_b = f.read()
                print(len(content_b))
        else:
            content_b = None

        articles_a = self.isolate_articles(content_a)
        articles_b = self.isolate_articles(content_b) if content_b else None

        if os.environ.get("GAZETTE_ENV", "dev") == "dev":
            return True
        elif articles_a == articles_b:
            print("Files are identical. No changes made.")
            return False
        else:
            shutil.copy2(file_a, file_b)
            os.remove(file_a)
            print(f"Files differed. '{file_b}' updated and '{file_a}' deleted.")
            return True


if __name__ == "__main__":
    gazette = Gazette()
    gazette.publish_gazette()
