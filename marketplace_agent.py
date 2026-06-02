import asyncio
import json
import os
import random
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding for Unicode characters in listing titles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from anthropic import Anthropic
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv(override=True)

FB_EMAIL = os.getenv("FB_EMAIL", "")
FB_PASSWORD = os.getenv("FB_PASSWORD", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
DB_PATH = os.getenv("DB_PATH", "marketplace.db")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

SCORING_SYSTEM = (
    "You are a resale arbitrage assistant. Score this Facebook Marketplace listing from 0-100 "
    "based on resale profit potential. High scores (70+): underpriced name-brand tools, electronics, "
    "appliances priced 40%+ below market. Low scores (<40): overpriced, no-name, broken, or AS-IS items. "
    'Return ONLY valid JSON: {"score": int, "reason": "one sentence", '
    '"suggested_offer": "dollar amount or null", "outreach_message": "personalized opener referencing the item"}'
)


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id TEXT UNIQUE NOT NULL,
            title TEXT,
            price TEXT,
            location TEXT,
            image_url TEXT,
            url TEXT,
            score INTEGER,
            reason TEXT,
            suggested_offer TEXT,
            outreach_message TEXT,
            status TEXT DEFAULT 'new',
            scraped_at TEXT
        )
    """)
    con.commit()
    con.close()


def listing_exists(listing_id: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT 1 FROM listings WHERE listing_id = ?", (listing_id,)).fetchone()
    con.close()
    return row is not None


def save_listing(data: dict):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """INSERT OR IGNORE INTO listings
           (listing_id, title, price, location, image_url, url,
            score, reason, suggested_offer, outreach_message, status, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)""",
        (
            data["listing_id"],
            data["title"],
            data["price"],
            data["location"],
            data["image_url"],
            data["url"],
            data["score"],
            data["reason"],
            data["suggested_offer"],
            data["outreach_message"],
            datetime.utcnow().isoformat(),
        ),
    )
    con.commit()
    con.close()


async def human_delay(min_ms: int = 800, max_ms: int = 2400):
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def login(page, email: str, password: str):
    print("[*] Navigating to Facebook login...")
    await page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")
    await human_delay(2000, 3500)

    # Wait for and fill email
    email_sel = None
    for sel in ["#email", 'input[name="email"]', 'input[type="email"]']:
        try:
            await page.wait_for_selector(sel, timeout=8000, state="visible")
            email_sel = sel
            break
        except PlaywrightTimeoutError:
            continue

    if not email_sel:
        await page.screenshot(path="login_debug.png")
        raise RuntimeError("Could not find email field â€” saved login_debug.png")

    # Click first to focus, then clear and type character by character (bypasses some bot checks)
    await page.click(email_sel)
    await human_delay(300, 600)
    await page.keyboard.press("Control+a")
    await page.keyboard.type(email, delay=random.uniform(80, 160))
    await human_delay(600, 1000)

    # Fill password
    pass_sel = None
    for sel in ["#pass", 'input[name="pass"]', 'input[type="password"]']:
        try:
            await page.wait_for_selector(sel, timeout=5000, state="visible")
            pass_sel = sel
            break
        except PlaywrightTimeoutError:
            continue

    if not pass_sel:
        raise RuntimeError("Could not find password field")

    await page.click(pass_sel)
    await human_delay(300, 600)
    await page.keyboard.type(password, delay=random.uniform(80, 160))
    await human_delay(800, 1400)

    # Submit: try button click, fall back to Enter key
    submitted = False
    for sel in ['button[name="login"]', 'button[type="submit"]', '[data-testid="royal_login_button"]']:
        try:
            btn = await page.wait_for_selector(sel, timeout=3000, state="visible")
            if btn:
                await btn.click()
                submitted = True
                break
        except PlaywrightTimeoutError:
            continue

    if not submitted:
        # Fallback: press Enter from password field
        await page.focus(pass_sel)
        await page.keyboard.press("Enter")

    # Wait for navigation away from /login
    try:
        await page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
    except PlaywrightTimeoutError:
        pass  # may still be on login â€” check below

    await human_delay(2000, 3000)
    current = page.url
    await page.screenshot(path="login_post.png")
    print(f"[*] Post-login URL: {current}")

    if "checkpoint" in current or "two_step" in current or "identity" in current or "login/device" in current:
        print("[!] Facebook requires verification â€” complete it in the browser window...")
        print("[*] Waiting for you to finish (up to 3 minutes)...")
        try:
            await page.wait_for_url(
                lambda url: "/login" not in url and "checkpoint" not in url and "two_step" not in url,
                timeout=180000,
            )
        except PlaywrightTimeoutError:
            pass
        current = page.url
        print(f"[*] Continuing â€” URL is now: {current}")

    if "/login" in current:
        raise RuntimeError(f"Login failed (still at {current}) â€” check credentials or saved login_post.png")

    print("[+] Logged in successfully")


async def search_marketplace(page, keyword: str, min_price: int = 0, max_price: int = 500) -> list[dict]:
    url = (
        f"https://www.facebook.com/marketplace/syracuse/search"
        f"?query={keyword.replace(' ', '%20')}"
        f"&minPrice={min_price}&maxPrice={max_price}"
        f"&daysSinceListed=7"
    )
    print(f"[*] Loading marketplace search: {url}")
    for attempt in range(3):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            break
        except Exception as e:
            print(f"  [!] Page load attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise
            # Recreate page on crash
            page = await page.context.new_page()
            await asyncio.sleep(2)
    await human_delay(2000, 4000)

    # Scroll to load more listings
    for _ in range(3):
        try:
            await page.keyboard.press("End")
        except Exception:
            break
        await human_delay(1200, 2000)

    listings = []
    cards = await page.query_selector_all('[data-testid="marketplace_feed_item"]')

    # Fallback selector for Facebook's varying DOM structures
    if not cards:
        cards = await page.query_selector_all('a[href*="/marketplace/item/"]')

    print(f"[*] Found {len(cards)} listing cards")

    for card in cards:
        try:
            href = await card.get_attribute("href") or ""
            if "/marketplace/item/" not in href:
                # Try navigating into parent link
                link_el = await card.query_selector('a[href*="/marketplace/item/"]')
                if link_el:
                    href = await link_el.get_attribute("href") or ""

            listing_id = ""
            if "/marketplace/item/" in href:
                parts = href.split("/marketplace/item/")
                listing_id = parts[1].strip("/").split("?")[0].split("/")[0]

            if not listing_id:
                continue

            # Collect all span texts
            all_spans = await card.query_selector_all('span[dir="auto"]')
            span_texts = []
            for el in all_spans:
                t = (await el.inner_text()).strip()
                if t:
                    span_texts.append(t)

            # Price: first span containing $ and short
            price = ""
            for t in span_texts:
                if "$" in t and len(t) < 25:
                    price = t
                    break
            # Also accept "Free" as price
            if not price:
                for t in span_texts:
                    if t.lower() == "free":
                        price = t
                        break

            # Title: longest span that isn't the price and isn't a badge like "Just listed"
            badges = {"just listed", "sold", "pending", "free"}
            title = "Unknown"
            best_len = 0
            for t in span_texts:
                if t == price:
                    continue
                if t.lower() in badges:
                    continue
                if "$" in t:
                    continue
                if len(t) > best_len:
                    best_len = len(t)
                    title = t

            # Location: short span, no $, not title, not badge
            location = ""
            for t in span_texts:
                if t == title or t == price or t.lower() in badges or "$" in t:
                    continue
                if 3 < len(t) < 60:
                    location = t
                    break

            # Image
            img_el = await card.query_selector("img")
            image_url = await img_el.get_attribute("src") if img_el else ""

            full_url = f"https://www.facebook.com{href}" if href.startswith("/") else href

            listings.append(
                {
                    "listing_id": listing_id,
                    "title": title,
                    "price": price,
                    "location": location,
                    "image_url": image_url,
                    "url": full_url,
                }
            )
        except Exception as e:
            print(f"  [!] Error parsing card: {e}")
            continue

    # Deduplicate by listing_id
    seen = set()
    unique = []
    for l in listings:
        if l["listing_id"] and l["listing_id"] not in seen:
            seen.add(l["listing_id"])
            unique.append(l)

    return unique


def score_listing(listing: dict) -> dict:
    prompt = (
        f"Title: {listing['title']}\n"
        f"Price: {listing['price']}\n"
        f"Location: {listing['location']}\n"
        f"URL: {listing['url']}"
    )
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=SCORING_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if not raw:
            raise ValueError("Empty response from Claude")
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
        # Extract JSON object if wrapped in extra text
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        return json.loads(raw)
    except Exception as e:
        print(f"  [!] Claude scoring error: {e}")
        return {
            "score": 0,
            "reason": "Scoring failed",
            "suggested_offer": None,
            "outreach_message": "",
        }


def score_label(score: int) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MID"
    return "LOW"


SESSION_FILE = "session.json"


async def run_agent(keyword: str, min_price: int = 0, max_price: int = 500):
    init_db()
    print(f"\n=== FB Marketplace Monitor | keyword='{keyword}' ${min_price}-${max_price} ===\n")

    session_exists = Path(SESSION_FILE).exists()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx_kwargs = dict(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        if session_exists:
            print("[*] Loading saved session (no login needed)")
            ctx_kwargs["storage_state"] = SESSION_FILE

        context = await browser.new_context(**ctx_kwargs)
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        try:
            if not session_exists:
                await login(page, FB_EMAIL, FB_PASSWORD)
                await context.storage_state(path=SESSION_FILE)
                print("[*] Session saved â€” future runs won't need 2FA")
            else:
                # Verify session is still valid
                await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
                await human_delay(1500, 2500)
                if "/login" in page.url:
                    print("[!] Saved session expired â€” logging in again...")
                    Path(SESSION_FILE).unlink(missing_ok=True)
                    await login(page, FB_EMAIL, FB_PASSWORD)
                    await context.storage_state(path=SESSION_FILE)

            listings = await search_marketplace(page, keyword, min_price, max_price)
        finally:
            await browser.close()

    new_count = 0
    for listing in listings:
        if listing_exists(listing["listing_id"]):
            continue

        print(f"\n[~] Scoring: {listing['title']} â€” {listing['price']}")
        scored = score_listing(listing)
        listing.update(scored)
        save_listing(listing)

        label = score_label(listing["score"])
        new_count += 1
        print(
            f"  [{label}] score={listing['score']} | {listing['reason']}\n"
            f"  offer={listing['suggested_offer']} | {listing['url']}"
        )
        await human_delay(500, 1000)

    print(f"\n=== Done. {new_count} new listings scored out of {len(listings)} found ===\n")


if __name__ == "__main__":
    import sys

    keyword = sys.argv[1] if len(sys.argv) > 1 else "tools"

from notifier import send_alert, ALERT_MIN_SCORE

async def run_agent():
    init_db()
    print(f"\n{'='*50}")
    print(f"FB Marketplace Agent | {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Keyword: {SEARCH_CONFIG['keyword']} | Max: ${SEARCH_CONFIG['max_price']}")
    print(f"{'='*50}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await login_facebook(page)
        listings = await scrape_marketplace(page, SEARCH_CONFIG)
        await browser.close()

    print(f"\nScored {len(listings)} new listings:\n")
    high_value = []

    for listing in listings:
        scored = score_listing(listing)
        listing.update(scored)
        save_listing(listing)
        score = scored.get("score", 0)
        flag = "HIGH" if score >= 70 else "MID" if score >= 50 else "LOW"
        print(f"[{flag}] [{score}] {listing['title']} -- ${listing['price']} -- {scored.get('reason','')}")
        if score >= 70:
            high_value.append(listing)

    print(f"\n{'='*50}")
    print(f"High-value alerts: {len(high_value)}")
    for item in high_value:
        print(f"\n  {item['title']} | ${item['price']}")
        print(f"  Offer: {item.get('suggested_offer')}")
        print(f"  Message: {item.get('outreach_message')}")
        print(f"  URL: {item['url']}")

    if high_value:
        send_alert(high_value)

if __name__ == "__main__":
    asyncio.run(run_agent())