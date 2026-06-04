import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

FROM_EMAIL = os.getenv("ALERT_EMAIL_FROM")
TO_EMAIL = os.getenv("ALERT_EMAIL_TO")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
ALERT_MIN_SCORE = int(os.getenv("ALERT_MIN_SCORE", "70"))


def send_alert(high_value_listings: list):
    if not high_value_listings:
        return

    subject = f"FB Marketplace Alert - {len(high_value_listings)} High-Value Listing(s)"

    rows_html = ""
    rows_text = ""

    for item in high_value_listings:
        score = item.get("score", 0)
        title = item.get("title", "Unknown")
        price = item.get("price", 0)
        location = item.get("location", "")
        reason = item.get("reason", "")
        offer = item.get("suggested_offer") or "-"
        message = item.get("outreach_message") or "-"
        url = item.get("url", "#")

        rows_html += f"""
        <div style="border:1px solid #e0e0e0;border-left:4px solid #3B6D11;border-radius:8px;padding:16px;margin-bottom:16px;font-family:Arial,sans-serif;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                <span style="font-size:16px;font-weight:600;color:#1a1a1a;">{title}</span>
                <span style="background:#EAF3DE;color:#3B6D11;font-size:12px;font-weight:600;padding:3px 10px;border-radius:99px;">Score {score}</span>
            </div>
            <div style="font-size:13px;color:#555;margin-bottom:6px;">${price} &nbsp; {location}</div>
            <div style="font-size:13px;color:#333;margin-bottom:10px;">{reason}</div>
            <div style="background:#f5f5f5;border-radius:6px;padding:10px 12px;font-size:13px;color:#222;margin-bottom:10px;font-style:italic;">
                "{message}"
            </div>
            <div style="font-size:13px;margin-bottom:8px;"><strong>Suggested offer:</strong> {offer}</div>
            <a href="{url}" style="display:inline-block;background:#3B6D11;color:white;font-size:13px;padding:8px 16px;border-radius:6px;text-decoration:none;">View Listing</a>
        </div>
        """

        rows_text += f"""
---
{title}
Price: ${price} | Location: {location} | Score: {score}
{reason}
Outreach: {message}
Suggested offer: {offer}
URL: {url}
"""

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <h2 style="color:#1a1a1a;margin-bottom:4px;">FB Marketplace - High Value Alerts</h2>
        <p style="color:#666;font-size:13px;margin-bottom:20px;">{len(high_value_listings)} listing(s) scored {ALERT_MIN_SCORE}+ this run.</p>
        {rows_html}
        <p style="font-size:11px;color:#999;margin-top:24px;">DJ AI Business Consultant LLC</p>
    </body></html>
    """

    text_body = f"FB Marketplace - {len(high_value_listings)} High-Value Alert(s)\n{rows_text}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(FROM_EMAIL, APP_PASSWORD)
            server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())
        print(f"Email alert sent -> {TO_EMAIL} ({len(high_value_listings)} listings)")
    except Exception as e:
        print(f"Email alert failed: {e}")


def send_wtb_alert(opportunities: list):
    if not opportunities:
        return

    subject = f"WTB Alert — {len(opportunities)} Profitable Sourcing Opportunities"

    rows_html = ""
    rows_text = ""

    for opp in opportunities:
        item = opp.get("item_wanted", "Unknown item")
        budget = opp.get("buyer_budget")
        source_price = opp.get("source_price")
        margin_pct = opp.get("margin_pct")
        margin_dollars = opp.get("margin_dollars")
        buyer_url = opp.get("buyer_url", "#")
        source_url = opp.get("source_url", "#")
        buyer_msg = opp.get("buyer_message_draft", "")
        score = opp.get("score", 0)
        platform = opp.get("source_platform", "")

        rows_html += f"""
        <div style="border:1px solid #e0e0e0;border-left:4px solid #1565C0;border-radius:8px;padding:16px;margin-bottom:16px;font-family:Arial,sans-serif;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                <span style="font-size:16px;font-weight:600;color:#1a1a1a;">{item}</span>
                <span style="background:#E3F2FD;color:#1565C0;font-size:12px;font-weight:600;padding:3px 10px;border-radius:99px;">Score {score}</span>
            </div>
            <div style="font-size:13px;color:#555;margin-bottom:6px;">
                Buyer budget: <strong>${budget}</strong> &nbsp;|&nbsp;
                Source price: <strong>${source_price}</strong> &nbsp;|&nbsp;
                Margin: <strong style="color:#2E7D32;">${margin_dollars} ({margin_pct}%)</strong>
            </div>
            <div style="font-size:12px;color:#888;margin-bottom:10px;">Source: {platform}</div>
            <div style="background:#f5f5f5;border-radius:6px;padding:10px 12px;font-size:13px;color:#222;margin-bottom:10px;font-style:italic;">
                "{buyer_msg}"
            </div>
            <div style="display:flex;gap:10px;">
                <a href="{buyer_url}" style="display:inline-block;background:#1565C0;color:white;font-size:13px;padding:8px 16px;border-radius:6px;text-decoration:none;">View Buyer Post</a>
                {f'<a href="{source_url}" style="display:inline-block;background:#2E7D32;color:white;font-size:13px;padding:8px 16px;border-radius:6px;text-decoration:none;">View Supply</a>' if source_url and source_url != "#" else ""}
            </div>
        </div>
        """

        rows_text += f"""
---
{item}
Buyer budget: ${budget} | Source: ${source_price} | Margin: ${margin_dollars} ({margin_pct}%)
Platform: {platform}
Message: {buyer_msg}
Buyer URL: {buyer_url}
Supply URL: {source_url}
"""

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <h2 style="color:#1a1a1a;margin-bottom:4px;">WTB Sourcing Opportunities</h2>
        <p style="color:#666;font-size:13px;margin-bottom:20px;">{len(opportunities)} deal(s) with {ALERT_MIN_SCORE}%+ margin found.</p>
        {rows_html}
        <p style="font-size:11px;color:#999;margin-top:24px;">DJ AI Business Consultant LLC</p>
    </body></html>
    """
    text_body = f"WTB Alert — {len(opportunities)} Opportunities\n{rows_text}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(FROM_EMAIL, APP_PASSWORD)
            server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())
        print(f"WTB alert sent -> {TO_EMAIL} ({len(opportunities)} opportunities)")
    except Exception as e:
        print(f"WTB alert failed: {e}")