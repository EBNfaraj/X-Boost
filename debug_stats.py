from app import app, db, ActionLog

with app.app_context():
    print("--- ActionLog Debug V2 ---")
    
    success_logs = ActionLog.query.filter_by(status='Success')
    
    # New Logic Simulation
    total_likes = success_logs.filter((ActionLog.action_type == 'like') | (ActionLog.action_type == 'both')).count()
    total_retweets = success_logs.filter((ActionLog.action_type == 'retweet') | (ActionLog.action_type == 'both')).count()
    
    print(f"Total Likes V2: {total_likes}")
    print(f"Total Retweets V2: {total_retweets}")
