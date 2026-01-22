"""
إضافة الأعمدة الجديدة لقاعدة البيانات الموجودة (Migration)
"""
from app import app, db
import sqlite3

db_path = 'xboost.db'

# الاتصال بقاعدة البيانات
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Adding new columns to support_task table...")

# إضافة الأعمدة الجديدة
try:
    cursor.execute("ALTER TABLE support_task ADD COLUMN accounts_used TEXT")
    print("✓ Added column: accounts_used")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("- Column accounts_used already exists")
    else:
        print(f"✗ Error adding accounts_used: {e}")

try:
    cursor.execute("ALTER TABLE support_task ADD COLUMN detailed_log TEXT")
    print("✓ Added column: detailed_log")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("- Column detailed_log already exists")
    else:
        print(f"✗ Error adding detailed_log: {e}")

try:
    cursor.execute("ALTER TABLE support_task ADD COLUMN last_error TEXT")
    print("✓ Added column: last_error")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("- Column last_error already exists")
    else:
        print(f"✗ Error adding last_error: {e}")

conn.commit()
conn.close()

print("\n✅ Migration completed successfully!")
print("Please restart the Flask application to apply changes.")
