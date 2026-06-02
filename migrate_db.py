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

conn.commit()
conn.close()
print("Migration complete.")
