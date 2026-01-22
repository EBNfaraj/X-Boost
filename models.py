from extensions import db
from datetime import datetime
import json

class CheckLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False) # Healthy, Suspended, Locked...
    response_time = db.Column(db.Integer, default=0) # ms
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    account = db.relationship('Account', backref=db.backref('health_logs', lazy=True))

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    cookies = db.Column(db.Text, nullable=True) # Stored as JSON string
    proxy = db.Column(db.String(255), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='Active') # Active, Suspended, Locked
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Stats
    likes_count = db.Column(db.Integer, default=0)
    retweets_count = db.Column(db.Integer, default=0)
    
    # Health Clinic
    health_status = db.Column(db.String(50), default='Unknown') # Healthy, Suspended, Locked, Invalid Cookies
    last_health_check = db.Column(db.DateTime, nullable=True)
    avg_response_time = db.Column(db.Float, default=0.0) # For human behavior scoring
    
    # Profile Details
    display_name = db.Column(db.String(100), nullable=True)
    profile_image_url = db.Column(db.String(500), nullable=True)

    def set_cookies(self, cookies_dict):
        self.cookies = json.dumps(cookies_dict)
    
    def get_cookies(self):
        return json.loads(self.cookies) if self.cookies else []

class SupportTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_url = db.Column(db.String(255), nullable=False)
    task_type = db.Column(db.String(20), nullable=False) # like, retweet, comment, follow
    status = db.Column(db.String(20), default='Pending') # Pending, In Progress, Completed
    target_count = db.Column(db.Integer, default=10) # How many interactions needed
    completed_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_time = db.Column(db.DateTime, default=datetime.utcnow) # For scheduled execution
    status = db.Column(db.String(20), default='Pending') # Pending, In Progress, Completed, Failed, Paused
    
    # Advanced settings & Logs
    is_paused = db.Column(db.Boolean, default=False)
    visible = db.Column(db.Boolean, default=True) # Soft delete
    error_log = db.Column(db.Text, nullable=True) # JSON list of errors
    
    # New fields for enhanced tracking
    accounts_used = db.Column(db.Text, nullable=True) # JSON array of account IDs used
    detailed_log = db.Column(db.Text, nullable=True) # Detailed execution log
    last_error = db.Column(db.Text, nullable=True) # Last error message
    
    min_delay = db.Column(db.Integer, default=30)
    max_delay = db.Column(db.Integer, default=120)

class TaskTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    target_url = db.Column(db.String(255), nullable=True)
    task_type = db.Column(db.String(20), default='like')
    target_count = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('support_task.id'), nullable=True)
    action_type = db.Column(db.String(20), nullable=False)
    target = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Success')
    details = db.Column(db.Text, nullable=True) # To store reply text or error msg

    account = db.relationship('Account', backref=db.backref('logs', lazy=True))

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # General
    app_name = db.Column(db.String(50), default='X-Boost Pro')
    
    # AI Configuration
    ai_provider = db.Column(db.String(20), default='groq') # groq, openai
    ai_api_key = db.Column(db.String(255), nullable=True)
    ai_model = db.Column(db.String(50), default='llama-3.1-8b-instant')
    ai_system_prompt = db.Column(db.Text, default='أنت مستخدم تويتر ذكي ولطيف. رد على التغريدة باللهجة البيضاء أو السعودية بشكل مختصر وجذاب. تجنب الهاشتاجات إلا للضرورة.')


class MonitoredAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    last_tweet_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    check_interval = db.Column(db.Integer, default=5) # Minutes
    task_type = db.Column(db.String(20), default='like') # like, retweet, both

    last_checked = db.Column(db.DateTime, nullable=True)
    
    # Visuals & Stats
    display_name = db.Column(db.String(100), nullable=True)
    profile_image_url = db.Column(db.String(500), nullable=True)
    stats_likes = db.Column(db.Integer, default=0)
    stats_retweets = db.Column(db.Integer, default=0)
    
    is_active = db.Column(db.Boolean, default=True) # Pause/Resume toggle

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    campaign_type = db.Column(db.String(50), nullable=False) # 'single_tweet', 'account_monitor'
    target_input = db.Column(db.String(255), nullable=False) # URL or Username
    actions = db.Column(db.String(255), nullable=False) # JSON: ['like', 'retweet']
    
    target_quantity = db.Column(db.Integer, default=10)
    completed_quantity = db.Column(db.Integer, default=0)
    
    speed = db.Column(db.Integer, default=3) # 1 (Fast) to 5 (Slow)
    status = db.Column(db.String(20), default='Active') # Active, Paused, Completed
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_time = db.Column(db.DateTime, nullable=True) # Future start time
    last_run = db.Column(db.DateTime, nullable=True)

class Proxy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Format: protocol://user:pass@host:port or just host:port
    proxy_string = db.Column(db.String(255), unique=True, nullable=False) 
    
    status = db.Column(db.String(20), default='Active') # Active, Dead, Slow
    last_checked = db.Column(db.DateTime, nullable=True)
    response_time = db.Column(db.Integer, default=0) # ms
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class SavedFilter(db.Model):
    """حفظ الفلاتر المخصصة للمستخدم"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    filter_data = db.Column(db.Text, nullable=False) # JSON: {status, type, search}
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_default = db.Column(db.Boolean, default=False) # هل يتم تطبيقه تلقائياً

class NotificationSettings(db.Model):
    """إعدادات الإشعارات"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Browser notifications
    browser_enabled = db.Column(db.Boolean, default=True)
    
    # Email notifications
    email_enabled = db.Column(db.Boolean, default=False)
    email_address = db.Column(db.String(255), nullable=True)
    
    # Telegram notifications
    telegram_enabled = db.Column(db.Boolean, default=False)
    telegram_chat_id = db.Column(db.String(100), nullable=True)
    
    # Notification triggers
    notify_on_complete = db.Column(db.Boolean, default=True)
    notify_on_fail = db.Column(db.Boolean, default=True)
    notify_on_pause = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
