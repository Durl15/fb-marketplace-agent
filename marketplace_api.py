import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Literal, Optional

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "marketplace.db")

app = FastAPI(title="FB Marketplace Monitor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def ensure_tables():
    with get_db() as con:
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
                scraped_at TEXT,
                source TEXT DEFAULT 'facebook',
                sold_price_avg REAL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS affiliate_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                total_revenue REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
        """)
        con.commit()


ensure_tables()


class StatusUpdate(BaseModel):
    status: Literal["contacted", "skipped", "new"]


class AffiliateCreate(BaseModel):
    name: str
    url: Optional[str] = None


class AffiliateStatusUpdate(BaseModel):
    status: Literal["active", "paused"]


@app.get("/listings")
def get_listings(
    min_score: int = Query(default=0, ge=0, le=100),
    status: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    with get_db() as con:
        query = "SELECT * FROM listings WHERE score >= ?"
        params: list = [min_score]

        if status and status != "all":
            query += " AND status = ?"
            params.append(status)

        if source and source != "all":
            query += " AND source = ?"
            params.append(source)

        query += " ORDER BY score DESC LIMIT ?"
        params.append(limit)

        rows = con.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@app.get("/stats")
def get_stats():
    with get_db() as con:
        total = con.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        high_value = con.execute(
            "SELECT COUNT(*) FROM listings WHERE score >= 70"
        ).fetchone()[0]
        contacted = con.execute(
            "SELECT COUNT(*) FROM listings WHERE status = 'contacted'"
        ).fetchone()[0]
        avg_row = con.execute("SELECT AVG(score) FROM listings WHERE score IS NOT NULL").fetchone()
        avg_score = round(avg_row[0] or 0, 1)
        fb_count = con.execute(
            "SELECT COUNT(*) FROM listings WHERE source = 'facebook' OR source IS NULL"
        ).fetchone()[0]
        ebay_count = con.execute(
            "SELECT COUNT(*) FROM listings WHERE source = 'ebay'"
        ).fetchone()[0]
        return {
            "total_scanned": total,
            "high_value": high_value,
            "contacted": contacted,
            "avg_score": avg_score,
            "facebook_count": fb_count,
            "ebay_count": ebay_count,
        }


@app.patch("/listings/{listing_id}/status")
def update_status(listing_id: int, body: StatusUpdate):
    with get_db() as con:
        result = con.execute(
            "UPDATE listings SET status = ? WHERE id = ?",
            (body.status, listing_id),
        )
        con.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Listing not found")
        return {"id": listing_id, "status": body.status}


@app.get("/affiliates")
def get_affiliates():
    with get_db() as con:
        rows = con.execute(
            "SELECT * FROM affiliate_links ORDER BY total_revenue DESC"
        ).fetchall()
        return [dict(r) for r in rows]


@app.post("/affiliates", status_code=201)
def create_affiliate(body: AffiliateCreate):
    created_at = datetime.now(timezone.utc).isoformat()
    with get_db() as con:
        cur = con.execute(
            "INSERT INTO affiliate_links (name, url, created_at) VALUES (?, ?, ?)",
            (body.name, body.url, created_at),
        )
        con.commit()
        row = con.execute(
            "SELECT * FROM affiliate_links WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return dict(row)


@app.patch("/affiliates/{affiliate_id}/status")
def update_affiliate_status(affiliate_id: int, body: AffiliateStatusUpdate):
    with get_db() as con:
        result = con.execute(
            "UPDATE affiliate_links SET status = ? WHERE id = ?",
            (body.status, affiliate_id),
        )
        con.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Affiliate not found")
        return {"id": affiliate_id, "status": body.status}


@app.get("/affiliates/report")
def affiliates_report():
    with get_db() as con:
        affiliates = [
            dict(r)
            for r in con.execute(
                "SELECT name, clicks, conversions, total_revenue, status FROM affiliate_links"
            ).fetchall()
        ]
        top_listings = [
            dict(r)
            for r in con.execute(
                "SELECT title, price, score, source, sold_price_avg, status FROM listings "
                "ORDER BY score DESC LIMIT 10"
            ).fetchall()
        ]
        stats = dict(
            con.execute(
                "SELECT COUNT(*) total, SUM(CASE WHEN score>=70 THEN 1 ELSE 0 END) high_value, "
                "SUM(CASE WHEN status='contacted' THEN 1 ELSE 0 END) contacted, "
                "AVG(score) avg_score FROM listings"
            ).fetchone()
        )

    aff_text = "\n".join(
        f"- {a['name']}: {a['clicks']} clicks, {a['conversions']} conversions, "
        f"${a['total_revenue']:.2f} revenue, {a['status']}"
        for a in affiliates
    ) or "No affiliates yet."

    listing_text = "\n".join(
        f"- [{r['score']}] {r['title']} — ${r['price']} ({r['source']})"
        for r in top_listings
    ) or "No listings yet."

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=(
            "You are a resale arbitrage analyst. Given marketplace performance data, "
            "write a concise plain-text weekly summary (no markdown headers or bullets) "
            "covering top opportunities, affiliate performance, and 2-3 specific recommendations."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Stats: {stats}\n\n"
                f"Top listings:\n{listing_text}\n\n"
                f"Affiliates:\n{aff_text}"
            ),
        }],
    )
    return {"report": msg.content[0].text, "generated_at": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("marketplace_api:app", host="0.0.0.0", port=8001, reload=True)
