import sqlite3
from datetime import datetime

DB_PATH = "arb.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS settings (
        user_id INTEGER PRIMARY KEY,
        source TEXT,
        exchanges TEXT,
        threshold REAL DEFAULT 1.0,
        trade_size REAL DEFAULT 1000,
        min_volume REAL DEFAULT 100000
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        ts TEXT,
        symbol TEXT,
        source TEXT,
        target TEXT,
        s_price REAL,
        t_price REAL,
        gross_spread REAL,
        net_spread REAL
    )""")
    conn.commit()
    conn.close()

def get_settings(user_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT source, exchanges, threshold, trade_size, min_volume "
        "FROM settings WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row

def save_settings(user_id, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT 1 FROM settings WHERE user_id=?", (user_id,))
    if not cur.fetchone():
        conn.execute("INSERT INTO settings (user_id) VALUES (?)", (user_id,))
    for k, v in kwargs.items():
        if v is not None:
            conn.execute(f"UPDATE settings SET {k}=? WHERE user_id=?", (v, user_id))
    conn.commit()
    conn.close()

def save_history(user_id, results):
    conn = sqlite3.connect(DB_PATH)
    ts = datetime.now().isoformat(timespec="seconds")
    conn.executemany(
        "INSERT INTO history (user_id, ts, symbol, source, target, "
        "s_price, t_price, gross_spread, net_spread) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        [(user_id, ts, r["symbol"], r["source"], r["target"],
          r["s_price"], r["t_price"], r["gross"], r["net"]) for r in results]
    )
    conn.commit()
    conn.close()

def get_top_history(user_id, limit=15):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT ts, symbol, source, target, net_spread "
        "FROM history WHERE user_id=? "
        "AND ts >= datetime('now','-1 day') "
        "ORDER BY net_spread DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return rows
