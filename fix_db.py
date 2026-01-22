import sqlite3

def fix_database():
    print("Connecting to database...")
    # Adjust path if your DB file is named differently or elsewhere
    # Usually Flask-SQLAlchemy defaults to instance/project.db or similar, 
    # but based on previous context chances are it is 'instance/database.db' or equal to where app.py is.
    # Let's try to assume it's created by default settings or look for .db files.
    # In the absence of specific config, we check 'instance/site.db' or similar.
    # However, checking app.py content for URI would be best.
    
    # Assuming 'messages.db' or similar based on typical tutorials, BUT
    # user has X-Boost Pro123.
    # Let's try to find it. 
    
    db_path = "xboost.db"
    # But wait, let's try to be generic or catch error.
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Checking monitored_account table...")
        
        # Check task_type
        try:
            cursor.execute("SELECT task_type FROM monitored_account LIMIT 1")
            print("task_type column exists.")
        except sqlite3.OperationalError:
            print("Adding task_type column...")
            cursor.execute("ALTER TABLE monitored_account ADD COLUMN task_type VARCHAR(20) DEFAULT 'like'")
            
        # Check last_checked
        try:
            cursor.execute("SELECT last_checked FROM monitored_account LIMIT 1")
            print("last_checked column exists.")
        except sqlite3.OperationalError:
            print("Adding last_checked column...")
            cursor.execute("ALTER TABLE monitored_account ADD COLUMN last_checked DATETIME")

        # New columns for Visuals & Stats
        new_columns = {
            'display_name': "VARCHAR(100)",
            'profile_image_url': "VARCHAR(500)",
            'stats_likes': "INTEGER DEFAULT 0",
            'stats_retweets': "INTEGER DEFAULT 0",
            'is_active': "BOOLEAN DEFAULT 1"
        }
        
        for col, dtype in new_columns.items():
            try:
                cursor.execute(f"SELECT {col} FROM monitored_account LIMIT 1")
                print(f"{col} column exists.")
            except sqlite3.OperationalError:
                print(f"Adding {col} column...")
                cursor.execute(f"ALTER TABLE monitored_account ADD COLUMN {col} {dtype}")

        # Check is_page_support
        try:
            cursor.execute("SELECT is_page_support FROM monitored_account LIMIT 1")
            print("is_page_support column exists.")
        except sqlite3.OperationalError:
            print("Adding is_page_support column...")
            cursor.execute("ALTER TABLE monitored_account ADD COLUMN is_page_support BOOLEAN DEFAULT 0")

        print("Checking account table (Health Clinic)...")
        # New columns for Account Health
        account_columns = {
            'health_status': "VARCHAR(50) DEFAULT 'Unknown'",
            'last_health_check': "DATETIME"
        }
        
        for col, dtype in account_columns.items():
            try:
                cursor.execute(f"SELECT {col} FROM account LIMIT 1")
                print(f"{col} column exists.")
            except sqlite3.OperationalError:
                print(f"Adding {col} column...")
                cursor.execute(f"ALTER TABLE account ADD COLUMN {col} {dtype}")


        print("Checking Settings table (AI Agent)...")
        
        # Check if we need to migrate from old Key-Value -> New Columns
        # Simplest way: Check if 'key' column exists. If so, drop table and recreate.
        try:
            cursor.execute("SELECT key FROM settings LIMIT 1")
            print("Old Settings table detected. Dropping and Recreating...")
            cursor.execute("DROP TABLE settings")
        except sqlite3.OperationalError:
            pass # Table might not exist or already new
            
        # Create Table (if not exists)
        create_settings_sql = """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            app_name VARCHAR(50) DEFAULT 'X-Boost Pro',
            ai_provider VARCHAR(20) DEFAULT 'groq',
            ai_api_key VARCHAR(255),
            ai_model VARCHAR(50) DEFAULT 'llama3-8b-8192',
            ai_system_prompt TEXT DEFAULT 'أنت مستخدم تويتر ذكي ولطيف. رد على التغريدة باللهجة البيضاء أو السعودية بشكل مختصر وجذاب. تجنب الهاشتاجات إلا للضرورة.'
        );
        """
        cursor.execute(create_settings_sql)
        
        # Initialize default if empty
        cursor.execute("SELECT count(*) FROM settings")
        if cursor.fetchone()[0] == 0:
             print("Initializing default settings...")
             cursor.execute("INSERT INTO settings (app_name, ai_provider, ai_model) VALUES ('X-Boost Pro', 'groq', 'llama-3.1-8b-instant')")
        else:
             # Force update legacy model to new one for ALL rows to be safe
             print("Forcing update to llama-3.1-8b-instant...")
             cursor.execute("UPDATE settings SET ai_model = 'llama-3.1-8b-instant'")
             print(f"Updated {cursor.rowcount} settings rows.")

        print("Checking ActionLog table...")
        try:
            cursor.execute("SELECT details FROM action_log LIMIT 1")
            print("details column exists.")
        except sqlite3.OperationalError:
            print("Adding details column to action_log...")
            cursor.execute("ALTER TABLE action_log ADD COLUMN details TEXT")
            
        print("Checking SupportTask table...")
        try:
            cursor.execute("SELECT scheduled_time FROM support_task LIMIT 1")
            print("scheduled_time column exists.")
        except sqlite3.OperationalError:
            print("Adding scheduled_time column to support_task...")
            cursor.execute("ALTER TABLE support_task ADD COLUMN scheduled_time DATETIME")

        print("Database schema fixed successfully!")
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        # Try finding the db file if possible?
        import os
        print("Current directory files:", os.listdir('.'))
        if os.path.exists('instance'):
            print("Instance folder:", os.listdir('instance'))

if __name__ == "__main__":
    fix_database()
