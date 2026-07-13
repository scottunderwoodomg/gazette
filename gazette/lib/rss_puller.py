import feedparser
import calendar
import logging
import re
from datetime import datetime, timezone
import os

from config.gazette_config import load_gazette_config
gazette_config = load_gazette_config()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
class RssPuller():
    def __init__(self, groups=None):
        self.output_file = gazette_config["rss_results"]

        self.rss_feeds = gazette_config["feeds"]
        self.start_date = gazette_config["start_date"]  # YYYY-MM-DD
        self.end_date   = gazette_config["end_date"]  # YYYY-MM-DD

        # If specific groups passed in, validate and use them; otherwise run all
        all_groups = list(self.rss_feeds.keys())
        if groups:
            invalid = [g for g in groups if g not in all_groups]
            if invalid:
                raise ValueError(f"Unknown group(s): {invalid}. Available: {all_groups}")
            self.active_groups = groups
        else:
            self.active_groups = all_groups

    def run_rss_puller(self):
        self.main()


    def parse_date(self, date_str):
        """Parse a YYYY-MM-DD string into an aware UTC datetime."""
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


    def entry_published_dt(self, entry):
        """Return a timezone-aware datetime for a feed entry, or None if unavailable."""
        time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if not time_struct:
            return None
        timestamp = calendar.timegm(time_struct)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)


    def pull_articles(self, feed_url, start_dt, end_dt):
        """Fetch a single feed and return matched (datetime, entry, feed_url) tuples."""
        logger.debug(f"  Fetching: {feed_url}")
        feed = feedparser.parse(feed_url)

        if feed.bozo and not feed.entries:
            raise ValueError(f"Could not parse feed — {feed.bozo_exception}")

        matched = []
        for entry in feed.entries:
            pub_dt = self.entry_published_dt(entry)
            if pub_dt is None:
                continue
            if start_dt <= pub_dt <= end_dt:
                matched.append((pub_dt, entry, feed_url))

        logger.debug(f"    → {len(matched)} article(s) matched")
        return matched


    def format_summary(self, entry):
        """Strip HTML from an entry summary and word-wrap at ~80 chars."""
        summary = entry.get("summary", "")
        if not summary:
            return ""
        summary = re.sub(r"<[^>]+>", "", summary).strip()
        words, line, lines = summary.split(), "", []
        for word in words:
            if len(line) + len(word) + 1 > 80:
                lines.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            lines.append(line)
        return lines


    def write_output(self, all_articles_by_group, feeds_by_group, start, end):
        output_path = self.output_file
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        total_articles = sum(len(a) for a in all_articles_by_group.values())
        total_feeds    = sum(len(f) for f in feeds_by_group.values())

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("RSS ARTICLE PULL\n")
            f.write("=" * 60 + "\n")
            f.write(f"Groups    : {len(feeds_by_group)}\n")
            f.write(f"Feeds     : {total_feeds}\n")
            f.write(f"Date range: {start} to {end}\n")
            f.write(f"Articles  : {total_articles} total\n")
            f.write(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n")

            global_index = 1

            for group_name, feeds in feeds_by_group.items():
                group_articles = all_articles_by_group[group_name]

                f.write(f"\n{'█' * 60}\n")
                f.write(f"GROUP: {group_name}\n")
                f.write(f"Articles: {len(group_articles)}\n")
                f.write(f"{'█' * 60}\n")

                by_feed = {url: [] for url in feeds}
                for pub_dt, entry, feed_url in group_articles:
                    by_feed[feed_url].append((pub_dt, entry))

                for feed_url in feeds:
                    articles = by_feed[feed_url]
                    f.write(f"\n{'─' * 60}\n")
                    f.write(f"FEED: {feed_url}\n")
                    f.write(f"Articles in range: {len(articles)}\n")
                    f.write(f"{'─' * 60}\n\n")

                    if not articles:
                        f.write("No articles found in the specified date range.\n\n")
                        continue

                    for pub_dt, entry in articles:
                        f.write(f"[{global_index}] {entry.get('title', 'No title')}\n")
                        f.write(f"    Published : {pub_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                        f.write(f"    Link      : {entry.get('link', 'N/A')}\n")
                        for ln in self.format_summary(entry):
                            f.write(f"    {ln}\n")
                        f.write("\n")
                        global_index += 1

        return output_path


    def main(self):
        if not self.rss_feeds:
            logger.error("ERROR: rss_feeds is empty. Add at least one feed URL.")
            return

        start_dt = self.parse_date(self.start_date)
        end_dt   = self.parse_date(self.end_date).replace(hour=23, minute=59, second=59)

        logger.debug(f"Pulling {len(self.active_groups)} group(s) from {self.start_date} to {self.end_date}…\n")

        all_articles_by_group = {}
        feeds_by_group        = {}
        errors                = []

        for group_name in self.active_groups:
            urls = self.rss_feeds[group_name]
            feeds_by_group[group_name]        = urls
            all_articles_by_group[group_name] = []

            logger.debug(f"Group: {group_name} ({len(urls)} feed(s))")
            for url in urls:
                try:
                    matched = self.pull_articles(url, start_dt, end_dt)
                    all_articles_by_group[group_name].extend(matched)
                except ValueError as e:
                    logger.warning(f"  WARNING: Skipping feed — {e}")
                    errors.append((url, str(e)))

            # Sort this group's articles chronologically
            all_articles_by_group[group_name].sort(key=lambda x: x[0])

        output_path = self.write_output(all_articles_by_group, feeds_by_group, self.start_date, self.end_date)

        total = sum(len(a) for a in all_articles_by_group.values())
        logger.debug(f"\nDone. {total} total article(s) written to: {output_path}")
        if errors:
            logger.error(f"\n{len(errors)} feed(s) had errors:")
            for url, err in errors:
                logger.error(f"  • {url}\n    {err}")

