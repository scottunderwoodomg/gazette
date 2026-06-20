email_content = {
    "html_body": """<!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
    <title>Daily Gazette</title>
    </head>
    <body style="margin:0;padding:0;background-color:#e4e4e4;">
    
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#e4e4e4;padding:36px 16px;">
        <tr>
        <td align="center">
            <table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;border-collapse:collapse;">
    
            <!-- MASTHEAD -->
            <tr>
                <td style="background-color:#111111;padding:40px 36px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                    <td width="136" valign="middle" style="padding-right:28px;">
                        {logo_html}
                    </td>
                    <td valign="middle">
                        <h1 style="
                        margin:0 0 10px 0;
                        font-family:'Trebuchet MS',Arial,Helvetica,sans-serif;
                        font-size:34px;
                        font-weight:700;
                        color:#ffffff;
                        letter-spacing:-0.02em;
                        line-height:1.05;
                        ">{recipient_name}'s Daily Gazette</h1>
                        <p style="
                        margin:0;
                        font-family:'Trebuchet MS',Arial,Helvetica,sans-serif;
                        font-size:10px;
                        font-weight:400;
                        color:#888888;
                        letter-spacing:0.2em;
                        text-transform:uppercase;
                        ">{date_str}</p>
                    </td>
                    </tr>
                </table>
                </td>
            </tr>
    
            <!-- Rule under masthead -->
            <tr>
                <td style="background-color:#333333;height:2px;font-size:0;line-height:0;">&nbsp;</td>
            </tr>
            <tr>
                <td style="background-color:#555555;height:1px;font-size:0;line-height:0;">&nbsp;</td>
            </tr>
    
            <!-- BODY -->
            <tr>
                <td style="background-color:#ffffff;">
                {sections_html}
                </td>
            </tr>
    
            <!-- FOOTER -->
            <tr>
                <td style="
                background-color:#111111;
                padding:14px 36px;
                text-align:center;
                font-family:'Trebuchet MS',Arial,Helvetica,sans-serif;
                font-size:9px;
                color:#555555;
                letter-spacing:0.18em;
                text-transform:uppercase;
                ">
                The Daily Gazette &nbsp;·&nbsp; Automated Edition &nbsp;·&nbsp; {date_str}
                </td>
            </tr>
    
            </table>
        </td>
        </tr>
    </table>
    
    </body>
    </html>""",
    "sections_html": """
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:0;border-collapse:collapse;">
            <tr>
                <td style="background-color:#ffffff;padding:28px 36px 32px 36px;{top_border}">
                <p style="
                    margin:0 0 6px 0;
                    font-family:'Trebuchet MS',Arial,Helvetica,sans-serif;
                    font-size:9px;
                    font-weight:700;
                    letter-spacing:0.25em;
                    text-transform:uppercase;
                    color:#999999;
                ">{section_title}</p>
                <div style="border-bottom:1px solid #e0e0e0;margin-bottom:20px;padding-bottom:0;"></div>
                <div>{content_html}</div>
                </td>
            </tr>
            </table>
            """,
}
