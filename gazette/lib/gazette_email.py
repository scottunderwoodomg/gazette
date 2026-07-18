import base64
import json
import logging
import os
import smtplib
from collections import OrderedDict
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown
from config.email_content_config import email_content
from config.gazette_config import load_gazette_config

gazette_config = load_gazette_config()
logger = logging.getLogger(__name__)


class GazetteEmail:
    def __init__(self):
        self.email_content = email_content

        self.email_username = os.environ["EMAIL_USERNAME"]
        self.email_password = os.environ["GMAIL_APP_PASSWORD"]
        self.email_target = os.environ["EMAIL_TARGET"]

        self.IMAGE_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "images"
        )

        self.SUMMARIES_FILE = gazette_config["rss_summary_file"]
        self.SCOREBOARD_FILE = gazette_config["scoreboard_cache_file"]

        self.logo_bytes = self.load_logo()

    # ── Entry point ───────────────────────────────────────────────

    def run_gazette_email(self):
        self.main()

    # ── Cache readers ─────────────────────────────────────────────

    def read_cache(self, path, payload_key, default, missing_msg, loaded_label):
        """Read a JSON cache file and return payload[payload_key], or `default` if missing."""
        if not os.path.exists(path):
            logger.debug(f"  {missing_msg}")
            return default
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        value = payload.get(payload_key, default)
        logger.debug(f"  Loaded {len(value)} {loaded_label}.")
        return value

    def read_summaries(self):
        return self.read_cache(
            self.SUMMARIES_FILE, "summaries", {},
            "No summaries cache found — email will contain scoreboard only.",
            "group summary/summaries",
        )

    def read_scoreboard(self):
        return self.read_cache(
            self.SCOREBOARD_FILE, "games", [],
            "No scoreboard cache found — email will contain summaries only.",
            "game(s) from scoreboard cache",
        )

    # ── Logo ──────────────────────────────────────────────────────

    def load_logo(self):
        logo_path = os.path.join(self.IMAGE_DIR, "gazette_logo.png")
        logger.debug(f"[load_logo] Looking at: {os.path.normpath(logo_path)}")
        logger.debug(f"[load_logo] Exists: {os.path.exists(logo_path)}")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                return f.read()
        return None

    # ── HTML builders ─────────────────────────────────────────────

    def build_sections_html(self, summaries_by_group):
        """Convert summaries dict into styled HTML section blocks."""
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

        return sections_html


    def render_game_card(self, g):
        """Render a single game as an HTML table cell."""
        state = g.get("state", "pre")
        score_block = ""

        next_line = ""
        if g.get("next_opponent") and g.get("next_game_time"):
            next_line = f"""<hr style="border:none;border-top:1px solid #e0e0e0;margin:8px 0 6px 0;">
            <p style="margin:0;font-family:'Trebuchet MS',Arial,sans-serif;font-size:9px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#bbbbbb;">Next {g['matched_team']} vs {g['next_opponent']}<br>{g['next_game_time']}</p>"""

        
        game_state_text = "Final" if state == "post" else g.get('detail', 'In Progress')
        
        game_state_link = (
            f'<a href="{g["recap_url"]}" style="color:#888888;text-decoration:underline;">{game_state_text}</a>'
            if g.get("recap_url")
            else f"{game_state_text}"
        )

        if state == "post":
            away_score = (
                int(g["away_score"]) if str(g.get("away_score", "")).isdigit() else 0
            )
            home_score = (
                int(g["home_score"]) if str(g.get("home_score", "")).isdigit() else 0
            )
            away_bold = (
                "font-weight:700;" if away_score > home_score else "font-weight:400;"
            )
            home_bold = (
                "font-weight:700;" if home_score > away_score else "font-weight:400;"
            )
            score_block = f"""
            <table cellpadding="0" cellspacing="0" style="width:100%;margin:6px 0 4px 0;">
              <tr>
                <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;{away_bold}color:#111111;padding:1px 0;">{g['away_abbr']}</td>
                <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;{away_bold}color:#111111;padding:1px 0;text-align:right;">{g['away_score']}</td>
              </tr>
              <tr>
                <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;{home_bold}color:#111111;padding:1px 0;">{g['home_abbr']}</td>
                <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;{home_bold}color:#111111;padding:1px 0;text-align:right;">{g['home_score']}</td>
              </tr>
            </table>
            <p style="margin:0 0 0 0;font-family:'Trebuchet MS',Arial,sans-serif;font-size:11px;color:#888888;">{game_state_link}</p>
            {next_line}"""

        elif state == "in":
            score_block = f"""
            <table cellpadding="0" cellspacing="0" style="width:100%;margin:6px 0 4px 0;">
              <tr>
                <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;font-weight:400;color:#111111;padding:1px 0;">{g['away_abbr']}</td>
                <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;font-weight:700;color:#111111;padding:1px 0;text-align:right;">{g['away_score']}</td>
              </tr>
              <tr>
                <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;font-weight:400;color:#111111;padding:1px 0;">{g['home_abbr']}</td>
                <td style="font-family:'Trebuchet MS',Arial,sans-serif;font-size:13px;font-weight:700;color:#111111;padding:1px 0;text-align:right;">{g['home_score']}</td>
              </tr>
            </table>
            <p style="margin:0 0 0 0;font-family:'Trebuchet MS',Arial,sans-serif;font-size:11px;color:#888888;">{game_state_link}</p>
            {next_line}"""

        else:  # pre
            score_block = f"""{next_line}"""

        date_label = (
            f'<p style="margin:0 0 4px 0;font-family:\'Trebuchet MS\',Arial,sans-serif;font-size:11px;color:#888888;">{g.get("kickoff", "")}</p>'
            if state in ["post","in"]
            else ""
        )

        return f"""<td style="width:25%;vertical-align:top;padding:12px 10px 12px 0;">
            {date_label}
            {score_block}
        </td>"""

    def build_scoreboard_html(self, games):
        """Render the scoreboard as an HTML section for the email."""
        if not games:
            return ""

        COLS = 4

        by_league = OrderedDict()
        for g in games:
            by_league.setdefault(g["league"], []).append(g)

        rows = []
        for league, league_games in by_league.items():
            rows.append({"type": "header", "league": league})
            for i in range(0, len(league_games), COLS):
                rows.append({"type": "games", "games": league_games[i : i + COLS]})

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
                game_cells = "".join(self.render_game_card(g) for g in row["games"])
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
        </table>"""

    def build_email_html(
        self, summaries_by_group, recipient_name, date_str, scoreboard_html
    ):
        sections_html = self.build_sections_html(summaries_by_group)

        if self.logo_bytes:
            logger.debug(f"Logo loaded: {len(self.logo_bytes)} bytes")
            logo_html = """<img
                src="cid:gazette_logo"
                width="120"
                height="120"
                alt="Gazette"
                style="display:block;width:120px;height:120px;object-fit:contain;filter:brightness(0)invert(1);"
            />"""
        else:
            logger.debug("Logo NOT loaded — falling back to G div")
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

        return self.email_content["html_body"].format_map(
            {
                "logo_html": logo_html,
                "recipient_name": recipient_name,
                "date_str": date_str,
                "sections_html": sections_html,
                "scoreboard_html": scoreboard_html,
            }
        )

    # ── Send ──────────────────────────────────────────────────────

    def send_email(self, html, date_str):
        msg = MIMEMultipart("related")
        msg["Subject"] = f"Your Daily Gazette — {date_str}"
        msg["From"] = self.email_username
        msg["To"] = self.email_target

        msg.attach(MIMEText(html, "html"))

        if self.logo_bytes:
            logo_img = MIMEImage(self.logo_bytes)
            logo_img.add_header("Content-ID", "<gazette_logo>")
            logo_img.add_header("Content-Disposition", "inline")
            msg.attach(logo_img)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(self.email_username, self.email_password)
            server.send_message(msg)

        logger.info(f"Email sent to {self.email_target}")

    # ── Main ──────────────────────────────────────────────────────

    def main(self):
        logger.debug("Reading summaries cache…")
        summaries_by_group = self.read_summaries()

        logger.debug("Reading scoreboard cache…")
        games = self.read_scoreboard()
        scoreboard_html = self.build_scoreboard_html(games)

        if not summaries_by_group and not scoreboard_html:
            logger.debug("Nothing to send — no summaries and no scoreboard data.")
            return

        date_str = datetime.now().strftime("%A, %B %-d, %Y")
        recipient_name = gazette_config.get("recipient_name", "Scott")

        html = self.build_email_html(
            summaries_by_group, recipient_name, date_str, scoreboard_html
        )

        self.send_email(html, date_str)
        logger.debug("\nDone.")
