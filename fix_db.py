"""
One-time database migration script.
Run from project root: python fix_db.py
Adds missing columns to the contact_messages table.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "medical.db")


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def fix_schema():
    print(f"[fix_db] Connecting to: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    migrations = [
        # (table, column, definition)
        ("contact_messages", "doctor_id",  "INTEGER REFERENCES doctors(id)"),
        ("contact_messages", "parent_id",  "INTEGER REFERENCES contact_messages(id)"),
        ("contact_messages", "is_read",    "BOOLEAN NOT NULL DEFAULT 0"),
        ("contact_messages", "sender_id",  "INTEGER REFERENCES users(id)"),
        ("users",            "phone",      "VARCHAR(20)"),
    ]

    changed = 0
    for table, col, defn in migrations:
        if not column_exists(cur, table, col):
            sql = f"ALTER TABLE {table} ADD COLUMN {col} {defn}"
            print(f"  [+] ALTER TABLE {table} ADD COLUMN {col}")
            cur.execute(sql)
            changed += 1
        else:
            print(f"  [=] {table}.{col} already exists — skipping")

    conn.commit()
    conn.close()

    if changed:
        print(f"\n[fix_db] ✅ Migration complete — {changed} column(s) added.")
    else:
        print("\n[fix_db] ✅ Schema is already up to date. Nothing changed.")

    # Verify final schema
    conn2 = sqlite3.connect(DB_PATH)
    cur2 = conn2.cursor()
    cur2.execute("PRAGMA table_info(contact_messages)")
    cols = [r[1] for r in cur2.fetchall()]
    print(f"\n[fix_db] contact_messages columns: {cols}")
    cur2.execute("PRAGMA table_info(users)")
    ucols = [r[1] for r in cur2.fetchall()]
    print(f"[fix_db] users columns: {ucols}")
    conn2.close()


if __name__ == "__main__":
    fix_schema()
