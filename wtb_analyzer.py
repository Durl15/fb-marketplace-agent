"""
wtb_analyzer.py — Claude analysis + supply matching + margin calculation
Called by wtb_agent.py, not run directly.
"""
import json
import os
import sqlite3
import sys

import anthropic
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(override=True)

DB_PATH = os.getenv("DB_PATH", "marketplace.db")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """You are a resale arbitrage assistant analyzing a buyer's wanted listing.
Extract the item they want and their maximum budget.
Then assess whether this can be sourced profitably.

Return ONLY valid JSON:
{
  "item_name": "clean item description (brand + model if mentioned)",
  "buyer_budget": 150.00,
  "sourceable": true,
  "source_query": "best eBay/marketplace search term to find this item",
  "buyer_message_draft": "short friendly message to send the buyer offering the item",
  "notes": "one sentence on why this is or is not a good flip opportunity"
}

buyer_budget should be null if no budget is mentioned.
sourceable should be false if item is not resalable (services, real estate, jobs, etc.).
buyer_message_draft: natural first message — introduce yourself, say you may have the item, ask if still needed."""


def analyze_wtb_listing(listing: dict) -> dict | None:
    """Call Claude to extract item details and draft outreach from a WTB listing."""
    title = listing.get("title", "")
    post_text = listing.get("buyer_post_text") or title
    price = listing.get("price")

    prompt = f"Wanted listing title: {title}\n"
    if price:
        prompt += f"Buyer budget mentioned: ${price}\n"
    if post_text and post_text != title:
        prompt += f"Full post text: {post_text}\n"

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
        return None
    except Exception as e:
        print(f"  [!] Claude error: {e}")
        return None


def find_supply_match(item_name: str, max_budget: float | None) -> dict | None:
    """Search marketplace.db listings for the cheapest matching supply item."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Build keyword filters from item name (first 3 meaningful words)
    keywords = [w for w in item_name.lower().split() if len(w) > 2][:3]
    if not keywords:
        conn.close()
        return None

    conditions = " AND ".join(f"LOWER(title) LIKE ?" for _ in keywords)
    params = [f"%{kw}%" for kw in keywords]

    query = f"""
        SELECT title, price, url, source, score
        FROM listings
        WHERE {conditions}
        AND status != 'skipped'
    """
    if max_budget:
        query += " AND CAST(REPLACE(REPLACE(price,'$',''),' ','') AS REAL) < ?"
        params.append(max_budget * 0.80)

    query += " ORDER BY CAST(REPLACE(REPLACE(price,'$',''),' ','') AS REAL) ASC LIMIT 1"

    try:
        row = conn.execute(query, params).fetchone()
        conn.close()
        if row:
            try:
                price_val = float(str(row["price"]).replace("$", "").replace(",", "").strip())
            except Exception:
                price_val = None
            return {
                "title": row["title"],
                "price": price_val,
                "url": row["url"],
                "source": row["source"],
            }
    except Exception as e:
        print(f"  [!] Supply match error: {e}")
        conn.close()

    return None


def calculate_margin(buyer_budget: float | None, source_price: float | None) -> dict:
    """Return margin_dollars, margin_pct, and score tier."""
    if not buyer_budget or not source_price or source_price >= buyer_budget:
        return {"margin_dollars": None, "margin_pct": None, "score": 0}

    margin_dollars = round(buyer_budget - source_price, 2)
    margin_pct = round((margin_dollars / buyer_budget) * 100, 1)

    if margin_pct >= 50:
        score = 90
    elif margin_pct >= 30:
        score = 75
    elif margin_pct >= 15:
        score = 50
    else:
        score = 25

    return {
        "margin_dollars": margin_dollars,
        "margin_pct": margin_pct,
        "score": score,
    }
