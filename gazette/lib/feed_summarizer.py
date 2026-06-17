import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

import anthropic
import markdown
from config.gazette_config import gazette_config


class FeedSummarizer:
    def __init__(self, groups=None):
        self.ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
        self.MODEL = gazette_config["model"]
        self.INTERESTS = gazette_config["interests"]

        self.email_username = os.environ["EMAIL_USERNAME"]
        self.email_password = os.environ["GMAIL_APP_PASSWORD"]
        self.email_target = os.environ["EMAIL_TARGET"]

        self.SCRIPT_DIR = "./cache/"
        self.INPUT_FILE = os.path.join(self.SCRIPT_DIR, "latest_rss_output.txt")
        self.OUTPUT_FILE = os.path.join(self.SCRIPT_DIR, "rss_summary.txt")

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
        """Runs the following:"""
        self.main()

    def parse_groups_from_file(self, raw_text):
        """
        Split raw article text into a dict of group_name: article_text
        based on GROUP: dividers written by the puller.
        """
        import re

        groups = {}
        # Split on the group header lines
        parts = re.split(r"█{60}\nGROUP: (.+?)\n.*?█{60}", raw_text, flags=re.DOTALL)
        # parts will be: [pre-content, group1_name, group1_body, group2_name, group2_body, ...]
        it = iter(parts[1:])  # skip the file header before the first group
        for group_name, group_body in zip(it, it):
            groups[group_name.strip()] = group_body.strip()
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
        """
        Ask Claude to return only the articles relevant to the given interests,
        preserving the original text block for each matched article verbatim.
        """
        interests_list = "\n".join(f"- {i}" for i in interests)
        return f"""You are a content filter. Below is a list of news articles, each separated by a blank line and starting with a numbered heading like [1], [2], etc.

    I am only interested in articles related to ANY of these topics:
    {interests_list}

    Instructions:
    - Read every article carefully.
    - Return ONLY the full text blocks of articles that are clearly relevant to at least one of the listed topics.
    - Interpret topics broadly and use good judgement — e.g. "schools" should match articles about education, teachers, students, universities, curriculum, etc.
    - Preserve each matching article's text exactly as it appears in the input.
    - Separate each returned article block with a blank line.
    - If NO articles match, respond with exactly: NO_MATCHES

    Do NOT add commentary, headings, or any extra text — only the matching article blocks (or NO_MATCHES).

    --- ARTICLES START ---
    {raw_text}
    --- ARTICLES END ---
    """

    def build_summary_prompt(self, filtered_text, interests):
        """Construct the summarisation prompt for the filtered article set."""
        interests_str = ", ".join(f'"{i}"' for i in interests)
        interest_note = (
            f"These articles were pre-filtered to topics matching: {interests_str}.\n"
            if interests
            else ""
        )
        return f"""Below is a collection of RSS news articles with their titles, publication dates, links, and summaries.
    {interest_note}
    Your task:
    1. Identify the major themes or topics across all the articles.
    2. For each theme, write a concise 1–2 sentence description.
    3. Under each theme, list the most relevant articles as bullet points using this exact format:
    - [Article Title](URL) — one-sentence relevance note

    Rules:
    - Keep the overall output tight and scannable.
    - Every article bullet must include the hyperlink in Markdown format.
    - If an article fits multiple themes, you may list it under more than one.
    - Do not invent information; only use what is in the articles provided.
    - Use plain Markdown (headers with ##, bullet points with -).

    --- ARTICLES START ---
    {filtered_text}
    --- ARTICLES END ---
    """

    def filter_articles(self, raw_text, interests, client, model):
        """
        Use Claude to filter the article list down to those matching INTERESTS.
        Returns the filtered text, or None if nothing matched.
        """
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
        """Send filtered articles to Claude and return the themed summary."""
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

    def write_summary(self, summaries_by_group, output_path):
        """Write per-group summaries to a single output file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("RSS ARTICLE SUMMARY\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source    : {self.INPUT_FILE}\n")
            f.write(f"Model     : {self.MODEL}\n")
            f.write(f"Groups    : {', '.join(summaries_by_group.keys())}\n")
            f.write("=" * 60 + "\n")

            for group_name, summary in summaries_by_group.items():
                interests = self.INTERESTS.get(group_name, [])
                f.write(f"\n{'█' * 60}\n")
                f.write(f"GROUP: {group_name}\n")
                f.write(
                    f"Interests : {', '.join(interests) if interests else 'all articles'}\n"
                )
                f.write(f"{'█' * 60}\n\n")
                f.write(summary)
                f.write("\n")

    def send_summary(self, summaries_by_group):
        # Concatenate all group summaries into a single markdown string
        summary_text = ""
        for group_name, summary in summaries_by_group.items():
            summary_text += f"# {group_name}\n\n"
            summary_text += summary
            summary_text += "\n\n"
        html = markdown.markdown(summary_text)
        msg = MIMEText(html,"html")
        msg["Subject"] = f"Gazette Summary — {datetime.now().strftime('%Y-%m-%d')}"
        msg["From"] = self.email_username
        msg["To"] = self.email_target

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(self.email_username, self.email_password)
            server.send_message(msg)

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

        # Split file into per-group article blocks
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

        if not summaries_by_group:
            print("No summaries generated — no articles matched any group's interests.")
            return

        self.send_summary(summaries_by_group)

        self.write_summary(summaries_by_group, self.OUTPUT_FILE)
        print(f"\nDone. Summary written to: {self.OUTPUT_FILE}")
