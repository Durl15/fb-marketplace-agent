"""
wtb_agent.py — WTB opportunity scanner
Scrapes Craigslist wanted + Facebook WTB, matches supply from marketplace.db,
calculates margin, and emails alerts for 30%+ deals.

Run: python wtb_agent.py
"""
import asyncio
import os
import sqlite3
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from playwright.async_api import async_playwright

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(override=True)

from notifier import send_wtb_alert
from scrapers.craigslist_wanted import fetch_craigslist_wanted
from scrapers.wtb_fb import fetch_fb_wtb
from wtb_analyzer import analyze_wtb_listing, calculate_margin, find_supply_match

DB_PATH = os.getenv("DB_PATH", "marketplace.db")
ALERT_MARGIN_PCT = float(os.getenv("ALERT_MIN_MARGIN_PCT", "30"))
LOCATION = os.getenv("MARKETPLACE_LOCATION", "syracuse")


def opportunity_exists(buyer_url: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT 1 FROM wtb_opportunities WHERE buyer_url=?", (buyer_url,)
    ).fetchone()
    conn.close()
    return row is not None


def save_opportunity(opp: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT OR IGNORE INTO wtb_opportunities
           (item_wanted, buyer_budget, buyer_url, buyer_post_text,
            buyer_message_draft, source_platform, source_url, source_price,
            margin_dollars, margin_pct, score, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,'new',?)""",
        (
            opp["item_wanted"],
            opp["buyer_budget"],
            opp["buyer_url"],
            opp.get("buyer_post_text", ""),
            opp["buyer_message_draft"],
            opp["source_platform"],
            opp.get("source_url"),
            opp.get("source_price"),
            opp.get("margin_dollars"),
            opp.get("margin_pct"),
            opp["score"],
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def process_listing(listing: dict, alert_opps: list):
    buyer_url = listing.get("url", "")
    if not buyer_url or opportunity_exists(buyer_url):
        return

    print(f"\n[~] {listing['title'][:70]}")

    analysis = analyze_wtb_listing(listing)
    if not analysis:
        return

    if not analysis.get("sourceable", False):
        print(f"  [skip] {analysis.get('notes', 'not sourceable')}")
        return

    item_name = analysis.get("item_name") or listing["title"]
    buyer_budget = analysis.get("buyer_budget") or listing.get("price")
    buyer_msg = analysis.get("buyer_message_draft", "")
    source_query = analysis.get("source_query", item_name)

    print(f"  Item: {item_name} | Budget: ${buyer_budget}")

    supply = find_supply_match(source_query, buyer_budget)
    source_price = supply["price"] if supply else None
    source_url = supply["url"] if supply else None

    margin = calculate_margin(buyer_budget, source_price)
    margin_dollars = margin["margin_dollars"]
    margin_pct = margin["margin_pct"]
    score = margin["score"]

    if margin_pct:
        print(f"  Supply: ${source_price} | Margin: ${margin_dollars} ({margin_pct}%)")
    else:
        print(f"  Supply: {f'${source_price}' if source_price else 'none found'} | No margin")

    opp = {
        "item_wanted": item_name,
        "buyer_budget": buyer_budget,
        "buyer_url": buyer_url,
        "buyer_post_text": listing.get("buyer_post_text", listing["title"]),
        "buyer_message_draft": buyer_msg,
        "source_platform": listing.get("source", "craigslist"),
        "source_url": source_url,
        "source_price": source_price,
        "margin_dollars": margin_dollars,
        "margin_pct": margin_pct,
        "score": score,
    }

    save_opportunity(opp)
    label = "HIGH" if score >= 75 else "MID" if score >= 50 else "LOW"
    print(f"  [{label}] score={score} | saved")

    if margin_pct and margin_pct >= ALERT_MARGIN_PCT:
        alert_opps.append({
            "item_wanted": item_name,
            "buyer_budget": buyer_budget,
            "buyer_url": buyer_url,
            "source_price": source_price,
            "source_url": source_url,
            "margin_dollars": margin_dollars,
            "margin_pct": margin_pct,
            "buyer_message_draft": buyer_msg,
            "score": score,
            "source_platform": listing.get("source", ""),
        })


async def run_wtb_agent():
    print("\n" + "=" * 55)
    print("  WTB Opportunity Scanner")
    print(f"  Location : {LOCATION}")
    print(f"  Alert at : {ALERT_MARGIN_PCT}%+ margin")
    print("=" * 55)

    alert_opps = []
    all_listings = []

    # 1. Craigslist wanted (no Playwright needed)
    cl = fetch_craigslist_wanted(LOCATION)
    all_listings.extend(cl)

    # 2. Facebook WTB (requires Playwright)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

            session_file = os.path.join(os.path.dirname(__file__), "session.json")
            if os.path.exists(session_file):
                import json as _json
                session_data = _json.load(open(session_file))
                cookies = session_data if isinstance(session_data, list) else session_data.get("cookies", [])
                if cookies:
                    await context.add_cookies(cookies)

            page = await context.new_page()
            fb_listings = await fetch_fb_wtb(page, LOCATION)
            all_listings.extend(fb_listings)
            await browser.close()
    except Exception as e:
        print(f"[fb_wtb] Skipped (Playwright error): {e}")

    print(f"\nTotal WTB listings to process: {len(all_listings)}")
    if not all_listings:
        print("No WTB listings found.")
        return

    for listing in all_listings:
        try:
            process_listing(listing, alert_opps)
        except Exception as e:
            print(f"  [!] Error processing '{listing.get('title','?')}': {e}")

    print(f"\n{'=' * 55}")
    print(f"  High-margin alerts (>={ALERT_MARGIN_PCT}%): {len(alert_opps)}")
    print(f"{'=' * 55}\n")

    if alert_opps:
        send_wtb_alert(alert_opps)


if __name__ == "__main__":
    asyncio.run(run_wtb_agent())
