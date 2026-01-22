"""
مساعد إعادة إنشاء قاعدة البيانات
"""
from app import app, db

with app.app_context():
    # إعادة إنشاء الجداول
    print("Creating database tables...")
    db.create_all()
    print("Database tables created successfully!")
