from flask_sqlalchemy import SQLAlchemy
from collections import deque

db = SQLAlchemy()
# Shared in-memory log stream (Max 50 items)
system_logs = deque(maxlen=50)

def add_system_log(message, type='info'):
    """Helper to add a log entry"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    system_logs.append({
        'time': timestamp,
        'message': message,
        'type': type
    })
