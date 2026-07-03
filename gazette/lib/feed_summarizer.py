import base64
import os
import re
import smtplib
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import anthropic
import markdown
from config.email_content_config import email_content
from config.gazette_config import load_gazette_config
from config.prompt_config import live_prompts

gazette_config = load_gazette_config()


class FeedSummarizer:
    def __init__(self, groups=None):
        self.PROMPTS = live_prompts
        self.email_content = email_content

        self.ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
        self.MODEL = gazette_config["model"]
        self.INTERESTS = gazette_config["interests"]

        self.email_username = os.environ["EMAIL_USERNAME"]
        self.email_password = os.environ["GMAIL_APP_PASSWORD"]
        self.email_target = os.environ["EMAIL_TARGET"]

        self.CACHE_DIR = "./cache/"
        self.IMAGE_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "images"
        )
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
        Skips groups with no articles.
        """
        groups = {}
        parts = re.split(r"█{60}\nGROUP: (.+?)\n.*?█{60}", raw_text, flags=re.DOTALL)
        it = iter(parts[1:])
        for group_name, group_body in zip(it, it):
            group_body = group_body.strip()
            # Skip groups with no article entries
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

    def read_scoreboard_cache(self):
        """Read scoreboard_cache.json and return the games list, or [] if missing."""
        import json

        cache_path = os.path.join(self.CACHE_DIR, "scoreboard_cache.json")
        if not os.path.exists(cache_path):
            print("  No scoreboard cache found — skipping scores section.")
            return []
        with open(cache_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        games = payload.get("games", [])
        print(f"  Loaded {len(games)} game(s) from scoreboard cache.")
        return games

    def build_filter_prompt(self, raw_text, interests):
        """
        Ask Claude to return only the articles relevant to the given interests,
        preserving the original text block for each matched article verbatim.
        """
        interests_list = "\n".join(f"- {i}" for i in interests)
        return self.PROMPTS["filter"].format_map(
            {
                "interests_list": interests_list,
                "raw_text": raw_text,
            }
        )

    def build_summary_prompt(self, filtered_text, interests):
        """Construct the summarisation prompt for the filtered article set."""
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

    def send_summary(self, summaries_by_group, scoreboard_html=""):
        date_str = datetime.now().strftime("%A, %B %-d, %Y")
        recipient_name = gazette_config.get("recipient_name", "Scott")

        html = self.build_email_html(
            summaries_by_group, recipient_name, date_str, scoreboard_html
        )

        # Use multipart/related to bundle HTML + inline image together
        msg = MIMEMultipart("related")
        msg["Subject"] = f"Your Daily Gazette — {date_str}"
        msg["From"] = self.email_username
        msg["To"] = self.email_target

        msg.attach(MIMEText(html, "html"))

        # Attach logo with a Content-ID so the HTML can reference it
        if self.LOGO_B64:
            logo_img = MIMEImage(base64.b64decode(self.LOGO_B64))
            logo_img.add_header("Content-ID", "<gazette_logo>")
            logo_img.add_header("Content-Disposition", "inline")
            msg.attach(logo_img)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(self.email_username, self.email_password)
            server.send_message(msg)

        print(f"Email sent to {gazette_config.get('recipient_name', 'Friend')}")

    def encode_logo(self):
        logo_path = os.path.join(self.IMAGE_DIR, "gazette_logo.png")
        print(f"[encode_logo] Looking at: {os.path.normpath(logo_path)}")
        print(f"[encode_logo] Exists: {os.path.exists(logo_path)}")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        return None

    def build_email_html(
        self, summaries_by_group, recipient_name, date_str, scoreboard_html
    ):
        sections_html = ""
        for i, (group_name, summary) in enumerate(summaries_by_group.items()):
            section_title = group_name.replace("_", " ").upper()
            content_html = markdown.markdown(summary)

            content_html = (
                content_html.replace(
                    "<h1>",
                    "<h1 style=\"font-family:'Trebuchet MS',Arial,Helvetica,sans-serif;font-size:16px;font-weight:700;color:#111111;margin:20px 0 4px 0;letter-spacing:-0.01em;\">",
                )
                .replace(
                    "<h2>",
                    "<h2 style=\"font-family:'Trebuchet MS',Arial,Helvetica,sans-serif;font-size:15px;font-weight:700;color:#111111;margin:20px 0 4px 0;letter-spacing:-0.01em;\">",
                )
                .replace(
                    "<h3>",
                    "<h3 style=\"font-family:'Trebuchet MS',Arial,Helvetica,sans-serif;font-size:13px;font-weight:700;color:#444444;margin:14px 0 2px 0;\">",
                )
                .replace(
                    "<p>",
                    "<p style=\"font-family:'Trebuchet MS',Arial,Helvetica,sans-serif;font-size:14px;line-height:1.75;color:#333333;margin:0 0 10px 0;\">",
                )
                .replace("<ul>", '<ul style="margin:4px 0 14px 0;padding-left:18px;">')
                .replace(
                    "<li>",
                    "<li style=\"font-family:'Trebuchet MS',Arial,Helvetica,sans-serif;font-size:14px;line-height:1.7;color:#333333;margin-bottom:8px;\">",
                )
                .replace(
                    "<a ",
                    '<a style="color:#111111;text-decoration:underline;font-weight:600;" ',
                )
            )

            top_border = "" if i == 0 else "border-top:2px solid #111111;"

            sections_html += self.email_content["sections_html"].format_map(
                {
                    "top_border": top_border,
                    "section_title": section_title,
                    "content_html": content_html,
                }
            )

        if self.LOGO_B64:
            print(f"Logo loaded: {len(self.LOGO_B64)} chars")
            logo_html = """<img
                src="cid:gazette_logo"
                width="120"
                height="120"
                alt="Gazette"
                style="display:block;width:120px;height:120px;object-fit:contain;filter:brightness(0)invert(1);"
            />"""
        else:
            print(f"Logo NOT loaded — falling back to G div")
            logo_html = """<div style="
                width:120px;height:120px;
                background:#ffffff;
                color:#111111;
                font-size:56px;
                font-weight:900;
                text-align:center;
                line-height:120px;
                font-family:Georgia,serif;
            ">G</div>"""

        html = self.email_content["html_body"].format_map(
            {
                "logo_html": logo_html,
                "recipient_name": recipient_name,
                "date_str": date_str,
                "sections_html": sections_html,
                "scoreboard_html": scoreboard_html,
            }
        )

        return html

    def build_scoreboard_html(self, games):
        """
        Render the scoreboard as an HTML section for the email.
        Games must already be sorted by league then game_time_iso (scoreboard.py does this).
        Presents in a 4-column grid with grey league header rows.
        """
        if not games:
            return ""

        COLS = 4
        from collections import OrderedDict

        by_league = OrderedDict()
        for g in games:
            by_league.setdefault(g["league"], []).append(g)

        rows = []
        for league, league_games in by_league.items():
            rows.append({"type": "header", "league": league})
            for i in range(0, len(league_games), COLS):
                rows.append({"type": "games", "games": league_games[i : i + COLS]})

        def render_game_card(g):
            state = g.get("state", "pre")

            if state == "post":
                away_score = (
                    int(g["away_score"])
                    if str(g.get("away_score", "")).isdigit()
                    else 0
                )
                home_score = (
                    int(g["home_score"])
                    if str(g.get("home_score", "")).isdigit()
                    else 0
                )
                away_bold = (
                    "font-weight:700;"
                    if away_score > home_score
                    else "font-weight:400;"
                )
                home_bold = (
                    "font-weight:700;"
                    if home_score > away_score
                    else "font-weight:400;"
                )
                score_block = f"""
                <table cellpadding="0" cellspacing="0" style="width:100%;margin:6px 0 8px 0;">
                    <tr>
                    <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;{away_bold}color:#111111;padding:1px 0;">{g['away_abbr']}</td>
                    <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;{away_bold}color:#111111;padding:1px 0;text-align:right;">{g['away_score']}</td>
                    </tr>
                    <tr>
                    <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;{home_bold}color:#111111;padding:1px 0;">{g['home_abbr']}</td>
                    <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;{home_bold}color:#111111;padding:1px 0;text-align:right;">{g['home_score']}</td>
                    </tr>
                </table>
                <p style="margin:0;font-family:'Trebuchet MS',Arial,sans-serif;font-size:11px;color:#888888;">Final</p>"""

            elif state == "in":
                score_block = f"""
                <table cellpadding="0" cellspacing="0" style="width:100%;margin:6px 0 8px 0;">
                    <tr>
                    <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;font-weight:400;color:#111111;padding:1px 0;">{g['away_abbr']}</td>
                    <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;font-weight:700;color:#111111;padding:1px 0;text-align:right;">{g['away_score']}</td>
                    </tr>
                    <tr>
                    <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;font-weight:400;color:#111111;padding:1px 0;">{g['home_abbr']}</td>
                    <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;font-weight:700;color:#111111;padding:1px 0;text-align:right;">{g['home_score']}</td>
                    </tr>
                </table>
                <p style="margin:0;font-family:'Trebuchet MS',Arial,sans-serif;font-size:11px;font-weight:700;color:#111111;">{g.get('detail','In Progress')}</p>"""

            else:  # pre
                score_block = f"""
                <table cellpadding="0" cellspacing="0" style="width:100%;margin:6px 0 8px 0;">
                    <tr><td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;font-weight:400;color:#111111;padding:1px 0;">{g['away_abbr']}</td></tr>
                    <tr><td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;font-weight:400;color:#111111;padding:1px 0;">{g['home_abbr']}</td></tr>
                </table>
                <p style="margin:0;font-family:'Trebuchet MS',Arial,sans-serif;font-size:11px;color:#888888;">{g.get('kickoff', g.get('detail',''))}</p>"""

            next_line = ""
            if g.get("next_opponent") and g.get("next_game_time"):
                next_line = f"""<p style="margin:6px 0 0 0;font-family:'Trebuchet MS',Arial,sans-serif;font-size:11px;color:#888888;line-height:1.4;">vs {g['next_opponent']}<br>{g['next_game_time']}</p>"""

            date_label = (
                f'<p style="margin:0 0 2px 0;font-family:\'Trebuchet MS\',Arial,sans-serif;font-size:11px;color:#888888;">{g.get("kickoff","")}</p>'
                if state == "post"
                else ""
            )

            return f"""<td style="width:25%;vertical-align:top;padding:12px 10px 12px 0;">
            {date_label}
            {score_block}
            {next_line}
            </td>"""

        rows_html = ""
        for row in rows:
            if row["type"] == "header":
                rows_html += f"""
                <tr>
                <td colspan="{COLS}" style="
                    background-color:#f2f2f2;
                    padding:7px 10px;
                    font-family:'Trebuchet MS',Arial,sans-serif;
                    font-size:10px;
                    font-weight:700;
                    letter-spacing:0.18em;
                    text-transform:uppercase;
                    color:#444444;
                    border-top:1px solid #e0e0e0;
                ">{row['league']}</td>
                </tr>"""
            else:
                game_cells = "".join(render_game_card(g) for g in row["games"])
                empty_cells = "".join(
                    '<td style="width:25%;padding:12px 10px 12px 0;"></td>'
                    for _ in range(COLS - len(row["games"]))
                )
                rows_html += f"<tr>{game_cells}{empty_cells}</tr>"

        return f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:0;border-collapse:collapse;">
        <tr>
            <td style="background-color:#ffffff;padding:28px 36px 32px 36px;border-top:2px solid #111111;">
            <p style="
                margin:0 0 6px 0;
                font-family:'Trebuchet MS',Arial,sans-serif;
                font-size:9px;
                font-weight:700;
                letter-spacing:0.25em;
                text-transform:uppercase;
                color:#999999;
            ">Scoreboard</p>
            <div style="border-bottom:1px solid #e0e0e0;margin-bottom:16px;"></div>
            <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                {rows_html}
            </table>
            </td>
        </tr>
        </table>
        """

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

        games = self.read_scoreboard_cache()
        scoreboard_html = self.build_scoreboard_html(games)

        self.send_summary(summaries_by_group, scoreboard_html)

        self.write_summary(summaries_by_group, self.OUTPUT_FILE)
        print(f"\nDone. Summary written to: {self.OUTPUT_FILE}")
