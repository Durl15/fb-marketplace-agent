import re
import requests
from datetime import datetime, timezone, timedelta

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _parse_price(text: str) -> float | None:
    m = re.search(r'\$[\s]*([\d,]+)', text or "")
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def fetch_craigslist_wanted(location: str = "syracuse") -> list:
    results = []
    urls = [
        f"https://{location}.craigslist.org/search/wan",
        f"https://{location}.craigslist.org/search/waa",
    ]

    for search_url in urls:
        try:
            r = requests.get(search_url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            html = r.text

            # Pattern: <li class="cl-static-search-result" title="TITLE">
            #            <a href="URL"><div class="title">TITLE</div>...
            pattern = re.compile(
                r'<li[^>]+cl-static-search-result[^>]+title="([^"]+)"[^>]*>\s*'
                r'<a\s+href="([^"]+)"',
                re.DOTALL
            )

            for m in pattern.finditer(html):
                title = m.group(1).strip()
                url = m.group(2).strip()

                if not title or not url:
                    continue

                # Extract price from title if present
                price = _parse_price(title)

                results.append({
                    "title": title,
                    "price": price,
                    "url": url,
                    "posted_at": None,
                    "source": "craigslist",
                })

        except Exception as e:
            print(f"[craigslist] Error fetching {search_url}: {e}")
            continue

    # Deduplicate by URL
    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    print(f"[craigslist] Found {len(unique)} wanted listings")
    return unique
