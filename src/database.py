import sqlite3
import pandas as pd

DB_PATH = "finpulse.db"
EXPECTED_COLUMNS = {
    "date": "TEXT",
    "description": "TEXT",
    "amount": "REAL",
    "category": "TEXT",
    "is_anomaly": "INTEGER DEFAULT 0",
    "merchant_normalized": "TEXT",
    "category_source": "TEXT",
    "category_confidence": "TEXT",
    "category_reason": "TEXT",
    "anomaly_score": "REAL DEFAULT 0",
    "anomaly_reason": "TEXT",
}


def get_connection():
    return sqlite3.connect(DB_PATH)


def create_tables():
    conn = get_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        description TEXT,
        amount REAL,
        category TEXT,
        is_anomaly INTEGER DEFAULT 0
        )"""
    )
    existing = {row[1] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()}
    for col, sql_type in EXPECTED_COLUMNS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE transactions ADD COLUMN {col} {sql_type}")
    conn.commit()
    conn.close()


def insert_transactions(df):
    conn = get_connection()
    safe_df = df.copy()
    for col in EXPECTED_COLUMNS:
        if col not in safe_df.columns:
            safe_df[col] = None
    safe_df.to_sql("transactions", conn, if_exists="append", index=False)
    conn.close()


def get_all_transactions():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM transactions", conn)
    conn.close()
    return df


def clear_transactions():
    conn = get_connection()
    conn.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()
