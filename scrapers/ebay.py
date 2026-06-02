import base64
import os
import time
import requests


BROWSE_API_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
FINDING_API_URL = "https://svcs.ebay.com/services/search/FindingService/v1"


def _get_access_token(app_id: str, cert_id: str) -> str:
    credentials = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data="grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope",
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_ebay_listings(config: dict) -> list:
    keyword = config["keyword"]
    min_price = config.get("min_price")
    max_price = config.get("max_price")
    max_results = config.get("max_results", 25)
    app_id = os.environ["EBAY_APP_ID"]
    cert_id = os.environ["EBAY_CERT_ID"]

    token = _get_access_token(app_id, cert_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        "Content-Type": "application/json",
    }

    filters = ["buyingOptions:{FIXED_PRICE}"]
    if min_price is not None and max_price is not None:
        filters.append(f"price:[{min_price:.2f}..{max_price:.2f}]")
    elif min_price is not None:
        filters.append(f"price:[{min_price:.2f}..]")
    elif max_price is not None:
        filters.append(f"price:[..{max_price:.2f}]")

    params = {
        "q": keyword,
        "limit": min(max_results, 200),
        "filter": ",".join(filters),
        "fieldgroups": "MATCHING_ITEMS",
    }

    resp = requests.get(BROWSE_API_URL, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    items = data.get("itemSummaries", [])
    results = []
    for item in items:
        try:
            price_val = float(item["price"]["value"])
        except (KeyError, ValueError):
            price_val = 0.0

        results.append({
            "id": item["itemId"],
            "title": item.get("title", ""),
            "price": price_val,
            "location": item.get("itemLocation", {}).get("city") or item.get("itemLocation", {}).get("stateOrProvince"),
            "url": item.get("itemWebUrl", ""),
            "image_url": item.get("image", {}).get("imageUrl"),
            "source": "ebay",
            "sold_price_avg": None,
        })

    return results


def fetch_keyword_sold_avg(keyword: str, app_id: str, max_results: int = 25) -> float | None:
    """Return the average sold price across recent completed eBay listings for a keyword.

    Called once per keyword (not per listing) to stay within Finding API rate limits.
    """
    params = {
        "OPERATION-NAME": "findCompletedItems",
        "SERVICE-VERSION": "1.0.0",
        "SECURITY-APPNAME": app_id,
        "RESPONSE-DATA-FORMAT": "JSON",
        "keywords": keyword,
        "itemFilter(0).name": "SoldItemsOnly",
        "itemFilter(0).value": "true",
        "paginationInput.entriesPerPage": max_results,
        "sortOrder": "EndTimeSoonest",
    }

    try:
        resp = requests.get(FINDING_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = (
            data.get("findCompletedItemsResponse", [{}])[0]
            .get("searchResult", [{}])[0]
            .get("item", [])
        )

        if not items:
            return None

        prices = []
        for item in items:
            try:
                price = float(
                    item["sellingStatus"][0]["currentPrice"][0]["__value__"]
                )
                if price > 0:
                    prices.append(price)
            except (KeyError, IndexError, ValueError):
                continue

        return round(sum(prices) / len(prices), 2) if prices else None

    except Exception as e:
        print(f"  [!] sold comps error: {e}")
        return None
