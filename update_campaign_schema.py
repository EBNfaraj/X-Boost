import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'xboost.db')

def update_schema():
    print(f"Connecting to database at {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='campaign'")
        if cursor.fetchone():
            print("Table 'campaign' already exists.")
        else:
            print("Creating 'campaign' table...")
            # Create table manually to match models.py
            cursor.execute("""
                CREATE TABLE campaign (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    campaign_type VARCHAR(50) NOT NULL,
                    target_input VARCHAR(255) NOT NULL,
                    actions VARCHAR(255) NOT NULL,
                    target_quantity INTEGER DEFAULT 10,
                    completed_quantity INTEGER DEFAULT 0,
                    speed INTEGER DEFAULT 3,
                    status VARCHAR(20) DEFAULT 'Active',
                    created_at DATETIME,
                    last_run DATETIME
                )
            """)
            print("Table 'campaign' created successfully.")
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_schema()
