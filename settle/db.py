import json
import sqlite3
import threading
import time

from . import config

_lock = threading.Lock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders(
  ref TEXT PRIMARY KEY, paypal_order_id TEXT, capture_id TEXT, email TEXT, name TEXT,
  items TEXT, amount REAL, currency TEXT, status TEXT, refunded REAL DEFAULT 0, created_at REAL);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, order_ref TEXT, text TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS cases(
  id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER, order_ref TEXT, status TEXT,
  engine TEXT, trace TEXT, proposal TEXT, checks TEXT, refund TEXT, reply TEXT,
  created_at REAL, updated_at REAL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
"""

DEFAULT_POLICY = (
    "Taller Luna - handmade ceramics. Returns & refunds policy:\n"
    "1. Item arrived broken or damaged: full refund, no need to send it back (a photo is welcome but not required under 40 EUR).\n"
    "2. Order not received 10+ days after purchase: full refund.\n"
    "3. Wrong item or wrong colour sent: offer a 20% partial refund to keep it, or a full refund if the customer insists.\n"
    "4. Changed mind within 30 days: full refund once the item is returned; ask the customer to ship it back first.\n"
    "5. Slight variations in glaze or colour are part of handmade pottery and are not defects; politely decline, offer 10% as goodwill if the customer is upset.\n"
    "6. Never refund more than what was paid. Be warm, short and reply in the customer's language."
)
DEFAULT_SETTINGS = {
    "policy": DEFAULT_POLICY,
    "auto_approve_limit": "30",      # refunds <= this amount can execute without a human click
    "min_confidence": "0.75",
    "max_refunds_per_customer_30d": "2",
    "autopilot": "on",
}


def conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
        for k, v in DEFAULT_SETTINGS.items():
            _conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        _conn.commit()
    return _conn


def q(sql, args=(), one=False):
    with _lock:
        cur = conn().execute(sql, args)
        rows = [dict(r) for r in cur.fetchall()]
        conn().commit()
        if one:
            return rows[0] if rows else None
        return rows


def ex(sql, args=()):
    with _lock:
        cur = conn().execute(sql, args)
        conn().commit()
        return cur.lastrowid


def settings():
    return {r["key"]: r["value"] for r in q("SELECT key,value FROM settings")}


def set_setting(k, v):
    ex("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, str(v)))


def get_order(ref):
    if not ref:
        return None
    o = q("SELECT * FROM orders WHERE ref=? OR paypal_order_id=?", (ref, ref), one=True)
    if o:
        o["items"] = json.loads(o["items"] or "[]")
    return o


def orders_by_email(email):
    rows = q("SELECT * FROM orders WHERE lower(email)=lower(?) ORDER BY created_at DESC", (email or "",))
    for o in rows:
        o["items"] = json.loads(o["items"] or "[]")
    return rows


def refunds_last_30d(email):
    since = time.time() - 30 * 86400
    r = q("SELECT COUNT(*) n FROM cases c JOIN orders o ON o.ref=c.order_ref "
          "WHERE lower(o.email)=lower(?) AND c.status='refunded' AND c.updated_at>?", (email or "", since), one=True)
    return r["n"] if r else 0


def case_full(cid):
    c = q("SELECT * FROM cases WHERE id=?", (cid,), one=True)
    if not c:
        return None
    for k in ("trace", "proposal", "checks", "refund"):
        c[k] = json.loads(c[k]) if c[k] else None
    c["message"] = q("SELECT * FROM messages WHERE id=?", (c["message_id"],), one=True)
    c["order"] = get_order(c["order_ref"])
    return c
