import json
import os
import re
from datetime import datetime

import anthropic
from config.gazette_config import load_gazette_config
from config.prompt_config import live_prompts

gazette_config = load_gazette_config()


class FeedSummarizer:
    def __init__(self, groups=None):
        self.PROMPTS = live_prompts

        self.ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
        self.MODEL = gazette_config["model"]
        self.INTERESTS = gazette_config["interests"]

        self.CACHE_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "cache"
        )
        self.INPUT_FILE = os.path.join(self.CACHE_DIR, "latest_rss_output.txt")
        self.OUTPUT_FILE = os.path.join(self.CACHE_DIR, "rss_summary.json")

        all_groups = list(self.INTERESTS.keys())
        if groups:
            invalid = [g for g in groups if g not in all_groups]
            if invalid:
                raise ValueError(
                    f"Unknown group(s): {invalid}. Available: {all_groups}"
                )
            self.active_groups = groups
        else:
            self.active_groups = all_groups

    # ─────────────────────────────────────────────

    def run_feed_summarizer(self):
        self.main()

    def parse_groups_from_file(self, raw_text):
        """
        Split raw article text into a dict of group_name: article_text
        based on GROUP: dividers written by the puller.
        Skips groups with no articles.
        """
        groups = {}
        parts = re.split(r"█{60}\nGROUP: (.+?)\n.*?█{60}", raw_text, flags=re.DOTALL)
        it = iter(parts[1:])
        for group_name, group_body in zip(it, it):
            group_body = group_body.strip()
            if not re.search(r"^\[\d+\]", group_body, re.MULTILINE):
                print(f"  Skipping group '{group_name.strip()}' — no articles found.")
                continue
            groups[group_name.strip()] = group_body
        return groups

    def read_articles(self, path):
        """Read the rss_output.txt file and return its raw contents."""
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Input file not found: {path}\n"
                "Run rss_puller.py first to generate rss_output.txt."
            )
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def build_filter_prompt(self, raw_text, interests):
        interests_list = "\n".join(f"- {i}" for i in interests)
        return self.PROMPTS["filter"].format_map(
            {
                "interests_list": interests_list,
                "raw_text": raw_text,
            }
        )

    def build_summary_prompt(self, filtered_text, interests):
        interests_str = ", ".join(f'"{i}"' for i in interests)
        interest_note = (
            f"These articles were pre-filtered to topics matching: {interests_str}.\n"
            if interests
            else ""
        )
        return self.PROMPTS["summary"].format_map(
            {
                "interest_note": interest_note,
                "filtered_text": filtered_text,
            }
        )

    def filter_articles(self, raw_text, interests, client, model):
        print(f"  Filtering articles for interests: {interests}")
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": self.build_filter_prompt(raw_text, interests),
                }
            ],
        )
        result = message.content[0].text.strip()
        if result == "NO_MATCHES":
            return None
        return result

    def summarise_articles(self, filtered_text, interests, client, model):
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": self.build_summary_prompt(filtered_text, interests),
                }
            ],
        )
        return message.content[0].text

    def save_summaries(self, summaries_by_group):
        """Save summaries to a JSON cache file for the email script to consume."""
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        payload = {
            "generated": datetime.now().isoformat(),
            "model": self.MODEL,
            "summaries": summaries_by_group,
        }
        with open(self.OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"  Summaries cached → {self.OUTPUT_FILE}")

    def main(self):
        if not self.ANTHROPIC_API_KEY:
            print(
                "ERROR: No Anthropic API key found.\n"
                "Get a key at: https://console.anthropic.com/settings/keys"
            )
            return

        client = anthropic.Anthropic(api_key=self.ANTHROPIC_API_KEY)

        print(f"Reading articles from: {self.INPUT_FILE}")
        try:
            raw_text = self.read_articles(self.INPUT_FILE)
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            return

        groups_from_file = self.parse_groups_from_file(raw_text)
        summaries_by_group = {}

        try:
            for i, group_name in enumerate(self.active_groups, 1):
                print(f"\nGroup {i}/{len(self.active_groups)}: {group_name}")

                if group_name not in groups_from_file:
                    print(
                        f"  WARNING: Group '{group_name}' not found in input file, skipping."
                    )
                    continue

                group_text = groups_from_file[group_name]
                interests = self.INTERESTS.get(group_name, [])

                if interests:
                    print(
                        f"  Step 1/2 — Filtering by interests ({len(interests)} topic(s))…"
                    )
                    filtered_text = self.filter_articles(
                        group_text, interests, client, self.MODEL
                    )
                    if filtered_text is None:
                        print(
                            f"  No articles matched interests for group '{group_name}', skipping."
                        )
                        continue
                else:
                    print(
                        f"  No interests defined — summarising all articles in group."
                    )
                    filtered_text = group_text

                step = "2/2" if interests else "1/1"
                print(f"  Step {step} — Summarising…")
                summary = self.summarise_articles(
                    filtered_text, interests, client, self.MODEL
                )
                summaries_by_group[group_name] = summary

        except anthropic.AuthenticationError:
            print(
                "ERROR: API key rejected. Check your key at: https://console.anthropic.com/settings/keys"
            )
            return
        except anthropic.APIError as e:
            print(f"ERROR: Anthropic API error — {e}")
            return

        if summaries_by_group:
            self.save_summaries(summaries_by_group)
            print(f"\nDone. {len(summaries_by_group)} group(s) summarised.")
        else:
            print(
                "\nNo summaries generated — no articles matched any group's interests."
            )
