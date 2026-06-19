import os
import smtplib
import base64
from datetime import datetime
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

import anthropic
import markdown
from config.gazette_config import gazette_config
from config.prompt_config import live_prompts

class FeedSummarizer:
    def __init__(self, groups=None):
        self.PROMPTS = live_prompts
        
        self.ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
        self.MODEL = gazette_config["model"]
        self.INTERESTS = gazette_config["interests"]

        self.email_username = os.environ["EMAIL_USERNAME"]
        self.email_password = os.environ["GMAIL_APP_PASSWORD"]
        self.email_target = os.environ["EMAIL_TARGET"]

        self.CACHE_DIR = "./cache/"
        self.IMAGE_DIR = "../images/"
        self.INPUT_FILE = os.path.join(self.CACHE_DIR, "latest_rss_output.txt")
        self.OUTPUT_FILE = os.path.join(self.CACHE_DIR, "rss_summary.txt")

        self.LOGO_B64 = self.encode_logo()

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
        return self.PROMPTS["filter"].format_map({
            "interests_list": interests_list,
            "raw_text": raw_text,
        })

    def build_summary_prompt(self, filtered_text, interests):
        """Construct the summarisation prompt for the filtered article set."""
        interests_str = ", ".join(f'"{i}"' for i in interests)
        interest_note = (
            f"These articles were pre-filtered to topics matching: {interests_str}.\n"
            if interests
            else ""
        )
        return self.PROMPTS["summary"].format_map({
            "interest_note": interest_note,
            "filtered_text": filtered_text,
        })

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
        date_str       = datetime.now().strftime("%A, %B %-d, %Y")
        recipient_name = gazette_config.get("recipient_name", "Scott")

        html = self.build_email_html(summaries_by_group, recipient_name, date_str)

        # Use multipart/related to bundle HTML + inline image together
        msg                 = MIMEMultipart("related")
        msg["Subject"]      = f"Your Daily Gazette — {date_str}"
        msg["From"]         = self.email_username
        msg["To"]           = self.email_target

        msg.attach(MIMEText(html, "html"))

        # Attach logo with a Content-ID so the HTML can reference it
        if self.LOGO_B64:
            logo_path = os.path.join(self.IMAGE_DIR, "gazette_logo.png")
            with open(logo_path, "rb") as f:
                logo_img = MIMEImage(f.read())
            logo_img.add_header("Content-ID", "<gazette_logo>")
            logo_img.add_header("Content-Disposition", "inline")
            msg.attach(logo_img)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(self.email_username, self.email_password)
            server.send_message(msg)

        print(f"Email sent to {gazette_config.get("recipient_name", "Friend")}")

    def encode_logo(self):
        logo_path = os.path.join(self.IMAGE_DIR, "gazette_logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        return None

    def build_email_html(self, summaries_by_group, recipient_name, date_str):
        # Section background colors — cycles if more than 3 groups
        section_colors = ["#E8F4FD", "#FEF3E2", "#E8F8F0", "#F3E8FD", "#FDE8E8"]

        # Build section blocks
        sections_html = ""
        for i, (group_name, summary) in enumerate(summaries_by_group.items()):
            color = section_colors[i % len(section_colors)]
            section_title = group_name.replace("_", " ").title()
            content_html  = markdown.markdown(summary)
            sections_html += f"""
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
            <tr>
                <td style="
                background-color: {color};
                border-left: 4px solid #111111;
                padding: 20px 24px;
                font-family: 'Georgia', serif;
                ">
                <p style="
                    margin: 0 0 12px 0;
                    font-family: 'Arial Black', 'Arial Bold', Arial, sans-serif;
                    font-size: 13px;
                    font-weight: 900;
                    letter-spacing: 0.12em;
                    text-transform: uppercase;
                    color: #111111;
                    border-bottom: 2px solid #111111;
                    padding-bottom: 8px;
                ">{section_title}</p>
                <div style="
                    font-family: Georgia, 'Times New Roman', serif;
                    font-size: 15px;
                    line-height: 1.7;
                    color: #1a1a1a;
                ">{content_html}</div>
                </td>
            </tr>
            </table>
            """

        # Logo block
        if self.LOGO_B64:
            logo_html = '''<img
                src="cid:gazette_logo"
                width="96"
                height="96"
                alt="Gazette"
                style="display:block;width:96px;height:96px;object-fit:contain;"
            />'''
        else:
            logo_html = '<div style="width:64px;height:64px;background:#111;color:#fff;font-size:28px;font-weight:900;text-align:center;line-height:64px;font-family:Georgia,serif;">G</div>'

        html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Daily Gazette</title>
    </head>
    <body style="margin:0;padding:0;background-color:#f0f0f0;font-family:Georgia,serif;">

    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f0f0;padding:32px 16px;">
        <tr>
        <td align="center">
            <table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;">

            <!-- HEADER -->
            <tr>
                <td style="padding-bottom: 24px; border-bottom: 3px double #111111; margin-bottom: 24px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                    <td width="80" valign="middle">{logo_html}</td>
                    <td valign="middle" style="padding-left: 16px;">
                        <h1 style="
                        margin: 0 0 4px 0;
                        font-family: Georgia, 'Times New Roman', serif;
                        font-size: 28px;
                        font-weight: 700;
                        color: #111111;
                        letter-spacing: -0.01em;
                        ">{recipient_name}'s Daily Gazette</h1>
                        <p style="
                        margin: 0;
                        font-family: Arial, sans-serif;
                        font-size: 12px;
                        color: #555555;
                        letter-spacing: 0.08em;
                        text-transform: uppercase;
                        ">{date_str}</p>
                    </td>
                    </tr>
                </table>
                </td>
            </tr>

            <!-- DIVIDER -->
            <tr><td style="height: 24px;"></td></tr>

            <!-- SECTIONS -->
            <tr>
                <td>{sections_html}</td>
            </tr>

            <!-- FOOTER -->
            <tr>
                <td style="
                border-top: 2px solid #111111;
                padding-top: 16px;
                text-align: center;
                font-family: Arial, sans-serif;
                font-size: 11px;
                color: #888888;
                letter-spacing: 0.06em;
                ">
                THE DAILY GAZETTE &nbsp;·&nbsp; AUTOMATED EDITION &nbsp;·&nbsp; {date_str}
                </td>
            </tr>

            </table>
        </td>
        </tr>
    </table>

    </body>
    </html>"""

        return html


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
