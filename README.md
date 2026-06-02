# FB Marketplace Monitor Agent

Playwright scraper + Claude scoring + FastAPI backend + React dashboard for Syracuse, NY arbitrage hunting.

## Setup

```powershell
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install Playwright browser
python -m playwright install chromium

# 3. Fill in credentials
# Edit .env — set FB_EMAIL, FB_PASSWORD, ANTHROPIC_API_KEY

# 4. Install frontend dependencies
cd frontend
npm install
cd ..
```

## Running

**Terminal 1 — Scrape and score listings:**
```powershell
# Usage: python marketplace_agent.py <keyword> <minPrice> <maxPrice>
python marketplace_agent.py tools 0 300
python marketplace_agent.py electronics 50 500
python marketplace_agent.py "power drill" 0 200
```

**Terminal 2 — Start API server:**
```powershell
python marketplace_api.py
# API runs at http://localhost:8001
```

**Terminal 3 — Start dashboard:**
```powershell
cd frontend
npm run dev
# Dashboard at http://localhost:5173
```

## Environment Variables

| Variable | Description |
|---|---|
| `FB_EMAIL` | Facebook account email |
| `FB_PASSWORD` | Facebook account password |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `HEADLESS` | `true` for headless browser, `false` (default) shows browser window |
| `DB_PATH` | SQLite database path (default: `marketplace.db`) |

## API

- `GET /listings?min_score=0&status=new&limit=100` — fetch listings
- `GET /stats` — aggregate stats
- `PATCH /listings/{id}/status` — update status (`new` | `contacted` | `skipped`)

## Score Guide

| Range | Label | Meaning |
|---|---|---|
| 70–100 | HIGH | Strong resale potential — act fast |
| 40–69 | MID | Moderate value — review manually |
| 0–39 | LOW | Overpriced, no-name, or broken |
