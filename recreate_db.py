"""
حذف قاعدة البيانات القديمة وإعادة إنشائها مع الأعمدة الجديدة
"""
from app import app, db
import os

# حذف قاعدة البيانات القديمة
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'xboost.db')
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted old database: {db_path}")

with app.app_context():
    # إعادة إنشاء الجداول
    print("Creating new database tables...")
    db.create_all()
    print("Database tables created successfully with new columns!")
