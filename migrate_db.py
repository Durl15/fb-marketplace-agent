import sqlite3

conn = sqlite3.connect("marketplace.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE listings ADD COLUMN source TEXT DEFAULT 'facebook'")
    print("Added column: source")
except sqlite3.OperationalError:
    print("Column already exists: source")

try:
    cursor.execute("ALTER TABLE listings ADD COLUMN sold_price_avg REAL")
    print("Added column: sold_price_avg")
except sqlite3.OperationalError:
    print("Column already exists: sold_price_avg")

try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wtb_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_wanted TEXT,
            buyer_budget REAL,
            buyer_url TEXT UNIQUE,
            buyer_post_text TEXT,
            buyer_message_draft TEXT,
            source_platform TEXT,
            source_url TEXT,
            source_price REAL,
            margin_dollars REAL,
            margin_pct REAL,
            score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'new',
            created_at TEXT
        )
    """)
    print("Created table: wtb_opportunities")
except sqlite3.OperationalError as e:
    print(f"wtb_opportunities: {e}")

conn.commit()
conn.close()
print("Migration complete.")
