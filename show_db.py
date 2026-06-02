import sqlite3
con = sqlite3.connect("marketplace.db")
rows = con.execute(
    "SELECT title, price, score, reason, suggested_offer FROM listings ORDER BY score DESC LIMIT 15"
).fetchall()
for r in rows:
    tier = "HIGH" if r[2] >= 70 else ("MID" if r[2] >= 40 else "LOW")
    print(f"[{tier}/{r[2]:3d}] {r[1]:>6} | {r[0][:45]} | {r[3][:55]}")
print()
total = con.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
high = con.execute("SELECT COUNT(*) FROM listings WHERE score >= 70").fetchone()[0]
mid = con.execute("SELECT COUNT(*) FROM listings WHERE score >= 40 AND score < 70").fetchone()[0]
print(f"Total: {total}  |  HIGH (70+): {high}  |  MID (40-69): {mid}")
con.close()
