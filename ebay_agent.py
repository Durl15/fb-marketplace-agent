import json
import os
import sqlite3
import sys
import time
from datetime import datetime

import anthropic
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from notifier import send_alert
from scrapers.ebay import fetch_ebay_listings, fetch_keyword_sold_avg
from log_pusher import push_log

load_dotenv(override=True)

EBAY_CONFIG = {
    "keywords": [k.strip() for k in os.getenv("EBAY_KEYWORDS", "tools").split(",")],
    "min_price": float(os.getenv("EBAY_MIN_PRICE", "0")),
    "max_price": float(os.getenv("EBAY_MAX_PRICE", "500")),
    "max_results": int(os.getenv("EBAY_MAX_RESULTS", "25")),
}

DB_PATH = os.getenv("DB_PATH", "marketplace.db")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SCORING_CRITERIA = (
    "You are a resale arbitrage assistant evaluating eBay listings. "
    "Score this listing 0-100 based on profit margin potential using sold price data. "
    "Primary signal: if sold_price_avg is available and the current price is 30%+ below it, "
    "that is a strong buy opportunity (score 70+). Listings at or above sold_price_avg score low (<40). "
    "Secondary signals: brand recognition, item condition, demand, resale velocity. "
    'Return ONLY valid JSON: {"score": int, "reason": "one sentence on the margin opportunity", '
    '"suggested_offer": "dollar amount or null", "outreach_message": "personalized opener or empty string"}'
)


def score_listing(listing: dict) -> dict:
    sold_avg = listing.get("sold_price_avg")
    sold_line = f"Average sold price: ${sold_avg:.2f}" if sold_avg else "Average sold price: N/A"
    prompt = (
        f"Title: {listing['title']}\n"
        f"Current price: ${listing['price']}\n"
        f"{sold_line}\n"
        f"Location: {listing.get('location') or 'N/A'}\n"
        f"URL: {listing['url']}"
    )
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=SCORING_CRITERIA,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        return json.loads(raw)
    except Exception as e:
        print(f"  [!] Claude scoring error: {e}")
        return {"score": 0, "reason": "Scoring failed", "suggested_offer": None, "outreach_message": ""}


def listing_exists(item_id: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT 1 FROM listings WHERE listing_id = ?", (item_id,)).fetchone()
    con.close()
    return row is not None


def save_listing(listing: dict):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """INSERT OR IGNORE INTO listings
           (listing_id, title, price, location, image_url, url,
            score, reason, suggested_offer, outreach_message,
            source, sold_price_avg, status, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)""",
        (
            listing["id"],
            listing["title"],
            str(listing["price"]),
            listing.get("location") or "",
            listing.get("image_url") or "",
            listing["url"],
            listing.get("score", 0),
            listing.get("reason", ""),
            listing.get("suggested_offer"),
            listing.get("outreach_message", ""),
            listing.get("source", "ebay"),
            listing.get("sold_price_avg"),
            datetime.utcnow().isoformat(),
        ),
    )
    con.commit()
    con.close()


def run():
    keywords = EBAY_CONFIG["keywords"]
    print(f"\n{'=' * 50}")
    print(f"eBay Agent | keywords={keywords}")
    print(f"Price range: ${EBAY_CONFIG['min_price']:.0f}-${EBAY_CONFIG['max_price']:.0f}")
    print(f"{'=' * 50}\n")

    high_value = []

    for keyword in keywords:
        print(f"\n[*] Fetching eBay listings for: '{keyword}'")
        config = {
            "keyword": keyword,
            "min_price": EBAY_CONFIG["min_price"],
            "max_price": EBAY_CONFIG["max_price"],
            "max_results": EBAY_CONFIG["max_results"],
        }
        try:
            listings = fetch_ebay_listings(config)
        except Exception as e:
            print(f"  [!] Fetch error for '{keyword}': {e}")
            continue

        print(f"  Found {len(listings)} listings")

        # One comp lookup per keyword — stays within Finding API rate limits
        app_id = os.environ["EBAY_APP_ID"]
        keyword_sold_avg = fetch_keyword_sold_avg(keyword, app_id)
        if keyword_sold_avg:
            print(f"  Sold comps for '{keyword}': avg=${keyword_sold_avg}")
        else:
            print(f"  Sold comps for '{keyword}': N/A")

        new_count = 0

        for listing in listings:
            if listing_exists(listing["id"]):
                continue

            listing["sold_price_avg"] = keyword_sold_avg

            print(f"\n[~] Scoring: {listing['title']} — ${listing['price']}")
            if keyword_sold_avg:
                margin = round((keyword_sold_avg - listing["price"]) / keyword_sold_avg * 100, 1)
                print(f"  sold_avg=${keyword_sold_avg} | margin={margin}%")
            else:
                print(f"  sold_avg=N/A")

            scored = score_listing(listing)
            listing.update(scored)
            save_listing(listing)

            score = listing.get("score", 0)
            label = "HIGH" if score >= 70 else "MID" if score >= 40 else "LOW"
            new_count += 1
            sold_avg = listing.get("sold_price_avg")
            print(
                f"  [{label}] score={score} | {listing.get('reason', '')}\n"
                f"  sold_avg=${sold_avg} | offer={listing.get('suggested_offer')} | {listing['url']}"
            )

            if score >= 70:
                high_value.append(listing)

        print(f"\n  Scored {new_count} new listings for '{keyword}'")

    print(f"\n{'=' * 50}")
    print(f"High-value alerts this run: {len(high_value)}")
    print(f"{'=' * 50}\n")

    if high_value:
        send_alert(high_value)

    push_log("ebay", os.path.join("logs", "ebay_agent.log"))


if __name__ == "__main__":
    run()
