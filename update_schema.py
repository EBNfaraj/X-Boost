import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'xboost.db')

def add_column():
    print(f"Connecting to database at {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(monitored_account)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'target_count' not in columns:
            print("Adding 'target_count' column to 'monitored_account' table...")
            cursor.execute("ALTER TABLE monitored_account ADD COLUMN target_count INTEGER DEFAULT 10")
            conn.commit()
            print("Column added successfully.")
        else:
            print("'target_count' column already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_column()
