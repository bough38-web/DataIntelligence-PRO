import sqlite3
import os
import json
from datetime import datetime

DB_DIR = os.path.expanduser("~/.dataintelligence_pro")
DB_PATH = os.path.join(DB_DIR, "database.sqlite3")
USERS_JSON = os.path.join(DB_DIR, "users.json")
LOGS_JSON = os.path.join(DB_DIR, "app_logs.json")

def get_connection():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            license TEXT UNIQUE NOT NULL,
            expiry TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Payments Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            payment_key TEXT,
            order_id TEXT,
            plan_name TEXT,
            status TEXT DEFAULT 'SUCCESS',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Logs Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT,
            action TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def migrate_from_json():
    """Migrate existing users.json and app_logs.json to SQLite if they exist and DB is empty."""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        if os.path.exists(USERS_JSON):
            with open(USERS_JSON, 'r', encoding='utf-8') as f:
                try:
                    users = json.load(f)
                    for u in users:
                        c.execute("INSERT OR IGNORE INTO users (name, phone, license, expiry) VALUES (?, ?, ?, ?)",
                                  (u.get('name'), u.get('phone', ''), u.get('license'), u.get('expiry')))
                except json.JSONDecodeError:
                    pass
                    
        if os.path.exists(LOGS_JSON):
            with open(LOGS_JSON, 'r', encoding='utf-8') as f:
                try:
                    logs = json.load(f)
                    for l in logs:
                        # JSON logs format is list of dicts or strings. Assuming dict with timestamp.
                        # For simplicity, just import if it's a dict.
                        if isinstance(l, dict):
                            c.execute("INSERT INTO logs (user_name, action, timestamp) VALUES (?, ?, ?)",
                                      (l.get('user', 'SYSTEM'), l.get('action', ''), l.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))
                except json.JSONDecodeError:
                    pass
        conn.commit()
    conn.close()

# --- CRUD Operations ---
def get_user_by_license(name, license_key):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE name = ? AND license = ?", (name, license_key))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_phone(phone):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(name, phone, license_key, expiry, role="user"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users (name, phone, license, expiry, role) VALUES (?, ?, ?, ?, ?)",
              (name, phone, license_key, expiry, role))
    conn.commit()
    conn.close()

def update_user_expiry(license_key, new_expiry):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET expiry = ? WHERE license = ?", (new_expiry, license_key))
    conn.commit()
    conn.close()

def add_log(user_name, action):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_name, action) VALUES (?, ?)", (user_name, action))
    conn.commit()
    conn.close()

def record_payment(user_id, amount, payment_key, order_id, plan_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO payments (user_id, amount, payment_key, order_id, plan_name) VALUES (?, ?, ?, ?, ?)",
              (user_id, amount, payment_key, order_id, plan_name))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return users

def get_metrics():
    conn = get_connection()
    c = conn.cursor()
    # Total revenue
    c.execute("SELECT SUM(amount) FROM payments WHERE status = 'SUCCESS'")
    revenue = c.fetchone()[0] or 0
    # Active users
    c.execute("SELECT COUNT(*) FROM users WHERE date(expiry) >= date('now')")
    active_users = c.fetchone()[0]
    # Total users
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    conn.close()
    return {"revenue": revenue, "active_users": active_users, "total_users": total_users}

# Initialize DB on load
init_db()
migrate_from_json()
