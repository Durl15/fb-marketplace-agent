import asyncio
import re
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv(override=True)

DB_PATH = os.getenv("DB_PATH", "marketplace.db")


def _existing_urls() -> set:
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT buyer_url FROM wtb_opportunities").fetchall()
        conn.close()
        return {r[0] for r in rows}
    except Exception:
        return set()


def _parse_price(text: str) -> float | None:
    m = re.search(r'\$[\s]*([\d,]+)', text or "")
    if m:
        return float(m.group(1).replace(",", ""))
    return None


async def fetch_fb_wtb(page, location: str = "syracuse") -> list:
    existing = _existing_urls()
    results = []

    url = f"https://www.facebook.com/marketplace/{location}/search?userType=c"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000 + int(2000 * __import__("random").random()))
    except Exception as e:
        print(f"[fb_wtb] Navigation error: {e}")
        return results

    try:
        # Primary: marketplace item cards
        cards = await page.query_selector_all('a[href*="/marketplace/item/"]')
        for card in cards:
            try:
                href = await card.get_attribute("href") or ""
                # Skip if userType=c not in URL context — WTB listings have different pattern
                full_url = f"https://www.facebook.com{href}" if href.startswith("/") else href
                full_url = full_url.split("?")[0]  # strip query params for dedup

                if full_url in existing:
                    continue

                text = (await card.inner_text()).strip()
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                title = lines[0] if lines else ""
                price_text = " ".join(lines)
                price = _parse_price(price_text)

                if not title or len(title) < 3:
                    continue

                listing_id_m = re.search(r'/item/(\d+)', full_url)
                listing_id = listing_id_m.group(1) if listing_id_m else ""

                results.append({
                    "title": title,
                    "price": price,
                    "url": full_url,
                    "listing_id": listing_id,
                    "source": "facebook_wtb",
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[fb_wtb] Primary selector failed: {e}")
        # Fallback: any marketplace item links
        try:
            links = await page.query_selector_all('a[href*="/marketplace/item/"]')
            for link in links:
                try:
                    href = await link.get_attribute("href") or ""
                    full_url = f"https://www.facebook.com{href}" if href.startswith("/") else href
                    full_url = full_url.split("?")[0]
                    if full_url in existing:
                        continue
                    text = (await link.inner_text()).strip()
                    title = text.splitlines()[0].strip() if text else ""
                    price = _parse_price(text)
                    listing_id_m = re.search(r'/item/(\d+)', full_url)
                    listing_id = listing_id_m.group(1) if listing_id_m else ""
                    if title and len(title) >= 3:
                        results.append({
                            "title": title,
                            "price": price,
                            "url": full_url,
                            "listing_id": listing_id,
                            "source": "facebook_wtb",
                        })
                except Exception:
                    continue
        except Exception as e2:
            print(f"[fb_wtb] Fallback selector failed: {e2}")

    # Deduplicate by URL
    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen and r["url"] not in existing:
            seen.add(r["url"])
            unique.append(r)

    print(f"[fb_wtb] Found {len(unique)} new WTB listings")
    return unique
