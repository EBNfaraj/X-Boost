from flask import Flask, render_template, jsonify, request, redirect, url_for, send_from_directory
from extensions import db
import os
import secrets
import json
import datetime
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Initialize Flask App
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = secrets.token_hex(16)
base_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'xboost.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
db.init_app(app)

# Custom Filters
@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return json.loads(value)
    except:
        return []

# Import Models
from models import Account, SupportTask, ActionLog, Settings, MonitoredAccount, Campaign, Proxy, CheckLog, TaskTemplate, SavedFilter, NotificationSettings
from core.engine import SupportEngine
import sys


# Initialize Engine (moved to __main__ block for reloader compatibility)

@app.route('/stream_logs')
def stream_logs():
    from extensions import system_logs
    return jsonify(list(system_logs))

@app.route('/')
def home():
    # Basic Stats
    active_accounts = Account.query.filter_by(status='Active').count()
    total_accounts = Account.query.count()
    total_actions = ActionLog.query.count()
    pending_tasks = SupportTask.query.filter_by(status='Pending').count()
    recent_logs = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(10).all()
    
    # Success Rate
    success_count = ActionLog.query.filter_by(status='Success').count()
    success_rate = round((success_count / total_actions * 100) if total_actions > 0 else 0)
    
    # Running Tasks
    running_tasks = SupportTask.query.filter_by(status='In Progress').count()
    
    # Active Now (accounts with activity in last 30 minutes)
    thirty_min_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
    active_now = Account.query.filter(Account.last_active >= thirty_min_ago).count()
    
    # Last Activity
    last_log = ActionLog.query.order_by(ActionLog.timestamp.desc()).first()
    if last_log:
        time_diff = datetime.datetime.utcnow() - last_log.timestamp
        minutes = int(time_diff.total_seconds() / 60)
        if minutes < 1:
            last_activity = "الآن"
        elif minutes < 60:
            last_activity = f"منذ {minutes} دقيقة"
        else:
            hours = minutes // 60
            last_activity = f"منذ {hours} ساعة"
    else:
        last_activity = "لا يوجد"
    
    # Alerts
    alerts = []
    
    # Suspended/Locked accounts alert
    suspended_count = Account.query.filter(Account.status.in_(['Suspended', 'Locked'])).count()
    if suspended_count > 0:
        alerts.append({
            'type': 'danger',
            'title': 'حسابات معلقة',
            'message': f'يوجد {suspended_count} حساب معلق أو مقفل',
            'time': ''
        })
    
    # Failed tasks alert
    failed_tasks = SupportTask.query.filter_by(status='Failed').count()
    if failed_tasks > 0:
        alerts.append({
            'type': 'warning',
            'title': 'مهام فاشلة',
            'message': f'يوجد {failed_tasks} مهمة فاشلة تحتاج المراجعة',
            'time': ''
        })
    
    # Accounts needing health check (not checked in 24 hours)
    one_day_ago = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    unchecked = Account.query.filter(
        (Account.last_health_check == None) | (Account.last_health_check < one_day_ago)
    ).count()
    if unchecked > 0:
        alerts.append({
            'type': 'info',
            'title': 'فحص صحي مطلوب',
            'message': f'{unchecked} حساب يحتاج فحص صحي',
            'time': ''
        })
    
    # Comparison Stats
    today = datetime.datetime.utcnow().date()
    today_start = datetime.datetime(today.year, today.month, today.day)
    
    # This week
    week_start = today_start - datetime.timedelta(days=today.weekday())
    week_current = ActionLog.query.filter(ActionLog.timestamp >= week_start).count()
    
    # Last week
    last_week_start = week_start - datetime.timedelta(days=7)
    week_previous = ActionLog.query.filter(
        ActionLog.timestamp >= last_week_start,
        ActionLog.timestamp < week_start
    ).count()
    
    week_change = round(((week_current - week_previous) / week_previous * 100) if week_previous > 0 else 0)
    
    # This month
    month_start = datetime.datetime(today.year, today.month, 1)
    month_current = ActionLog.query.filter(ActionLog.timestamp >= month_start).count()
    
    # Last month
    if today.month == 1:
        last_month_start = datetime.datetime(today.year - 1, 12, 1)
    else:
        last_month_start = datetime.datetime(today.year, today.month - 1, 1)
    month_previous = ActionLog.query.filter(
        ActionLog.timestamp >= last_month_start,
        ActionLog.timestamp < month_start
    ).count()
    
    month_change = round(((month_current - month_previous) / month_previous * 100) if month_previous > 0 else 0)
    
    return render_template('index.html', 
                          active_accounts=active_accounts,
                          total_actions=total_actions, 
                          pending_tasks=pending_tasks,
                          recent_logs=recent_logs,
                          success_rate=success_rate,
                          running_tasks=running_tasks,
                          active_now=active_now,
                          last_activity=last_activity,
                          alerts=alerts,
                          week_current=week_current,
                          week_previous=week_previous,
                          week_change=week_change,
                          month_current=month_current,
                          month_previous=month_previous,
                          month_change=month_change)

@app.route('/accounts')
def accounts():
    all_accounts = Account.query.all()
    
    # Calculate Stats
    total_accounts = len(all_accounts)
    active_accounts = sum(1 for acc in all_accounts if acc.status == 'Active')
    suspended_accounts = sum(1 for acc in all_accounts if acc.status in ['Suspended', 'Locked'])
    
    # Calculate Total Interactions (Likes + Retweets)
    total_interactions = sum(acc.likes_count + acc.retweets_count for acc in all_accounts)
    
    # Calculate total likes and retweets separately for charts
    total_likes = sum(acc.likes_count for acc in all_accounts)
    total_retweets = sum(acc.retweets_count for acc in all_accounts)
    
    return render_template('accounts.html', 
                          accounts=all_accounts,
                          total_accounts=total_accounts,
                          active_accounts=active_accounts,
                          suspended_accounts=suspended_accounts,
                          total_interactions=total_interactions,
                          total_likes=total_likes,
                          total_retweets=total_retweets)


# ===== Accounts API Endpoints =====

@app.route('/api/accounts/charts')
def api_accounts_charts():
    """Get chart data for accounts page"""
    # Status distribution
    active = Account.query.filter_by(status='Active').count()
    suspended = Account.query.filter_by(status='Suspended').count()
    locked = Account.query.filter_by(status='Locked').count()
    other = Account.query.filter(~Account.status.in_(['Active', 'Suspended', 'Locked'])).count()
    
    # Interactions
    all_accounts = Account.query.all()
    total_likes = sum(acc.likes_count for acc in all_accounts)
    total_retweets = sum(acc.retweets_count for acc in all_accounts)
    
    # Activity timeline (last 7 days per account)
    today = datetime.datetime.utcnow().date()
    timeline = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_start = datetime.datetime(day.year, day.month, day.day)
        day_end = day_start + datetime.timedelta(days=1)
        
        count = ActionLog.query.filter(
            ActionLog.timestamp >= day_start,
            ActionLog.timestamp < day_end
        ).count()
        timeline.append({
            'date': day.strftime('%m/%d'),
            'count': count
        })
    
    return jsonify({
        'status_distribution': {
            'active': active,
            'suspended': suspended,
            'locked': locked,
            'other': other
        },
        'interactions': {
            'likes': total_likes,
            'retweets': total_retweets
        },
        'timeline': timeline
    })


@app.route('/api/accounts/export/<format>')
def api_accounts_export(format):
    """Export accounts in different formats"""
    all_accounts = Account.query.all()
    
    accounts_data = []
    for acc in all_accounts:
        accounts_data.append({
            'id': acc.id,
            'username': acc.username,
            'status': acc.status,
            'proxy': acc.proxy or '',
            'likes_count': acc.likes_count,
            'retweets_count': acc.retweets_count,
            'health_status': acc.health_status,
            'last_active': acc.last_active.isoformat() if acc.last_active else None,
            'cookies': acc.cookies or ''
        })
    
    if format == 'json':
        response = app.response_class(
            response=json.dumps(accounts_data, ensure_ascii=False, indent=2),
            status=200,
            mimetype='application/json'
        )
        response.headers['Content-Disposition'] = 'attachment; filename=accounts_export.json'
        return response
    
    elif format == 'csv':
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['id', 'username', 'status', 'proxy', 'likes_count', 'retweets_count', 'health_status', 'last_active', 'cookies'])
        writer.writeheader()
        for acc in accounts_data:
            writer.writerow(acc)
        
        response = app.response_class(
            response=output.getvalue(),
            status=200,
            mimetype='text/csv'
        )
        response.headers['Content-Disposition'] = 'attachment; filename=accounts_export.csv'
        return response
    
    else:
        return jsonify({'error': 'Unsupported format'}), 400


@app.route('/api/accounts/import', methods=['POST'])
def api_accounts_import():
    """Import accounts from JSON or CSV"""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'لم يتم تحديد ملف'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'لم يتم تحديد ملف'}), 400
    
    filename = file.filename.lower()
    
    try:
        if filename.endswith('.json'):
            content = file.read().decode('utf-8')
            accounts_data = json.loads(content)
        elif filename.endswith('.csv'):
            import csv
            import io
            content = file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            accounts_data = list(reader)
        else:
            return jsonify({'status': 'error', 'message': 'صيغة الملف غير مدعومة. استخدم JSON أو CSV'}), 400
        
        imported = 0
        updated = 0
        errors = []
        
        for acc_data in accounts_data:
            username = acc_data.get('username', '').strip()
            if not username:
                errors.append('سطر بدون اسم مستخدم')
                continue
            
            # Check if exists
            existing = Account.query.filter_by(username=username).first()
            
            if existing:
                # Update
                if acc_data.get('proxy'):
                    existing.proxy = acc_data.get('proxy')
                if acc_data.get('cookies'):
                    existing.cookies = acc_data.get('cookies')
                if acc_data.get('status'):
                    existing.status = acc_data.get('status')
                updated += 1
            else:
                # Create new
                new_acc = Account(
                    username=username,
                    proxy=acc_data.get('proxy', ''),
                    cookies=acc_data.get('cookies', ''),
                    status=acc_data.get('status', 'Active')
                )
                db.session.add(new_acc)
                imported += 1
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'تم استيراد {imported} حساب جديد، وتحديث {updated} حساب',
            'imported': imported,
            'updated': updated,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/accounts/activity/<int:account_id>')
def api_account_activity(account_id):
    """Get detailed activity for a specific account"""
    account = Account.query.get_or_404(account_id)
    
    # Get recent logs
    logs = ActionLog.query.filter_by(account_id=account_id).order_by(ActionLog.timestamp.desc()).limit(20).all()
    
    logs_data = []
    for log in logs:
        logs_data.append({
            'id': log.id,
            'action_type': log.action_type,
            'target': log.target,
            'status': log.status,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'details': log.details
        })
    
    # Daily activity for last 7 days
    today = datetime.datetime.utcnow().date()
    daily_activity = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_start = datetime.datetime(day.year, day.month, day.day)
        day_end = day_start + datetime.timedelta(days=1)
        
        count = ActionLog.query.filter(
            ActionLog.account_id == account_id,
            ActionLog.timestamp >= day_start,
            ActionLog.timestamp < day_end
        ).count()
        daily_activity.append({
            'date': day.strftime('%m/%d'),
            'count': count
        })
    
    return jsonify({
        'account': {
            'last_active': account.last_active.strftime('%Y-%m-%d %H:%M') if account.last_active else 'N/A'
        },
        'status': 'success',
        'logs': logs_data,
        'daily_activity': daily_activity
    })


# ===== Health Check APIs =====

@app.route('/api/health/check_parallel', methods=['POST'])
def api_health_check_parallel():
    """Run health checks in parallel"""
    data = request.json
    account_ids = data.get('ids', [])
    
    if not account_ids:
        # If no IDs provided, check all
        accounts = Account.query.all()
        account_ids = [acc.id for acc in accounts]
    
    # helper function for single check
    def check_single_account(account_id):
        with app.app_context():
            try:
                account = Account.query.get(account_id)
                if not account: return None
                
                # Simulate check (replace with actual selenium/request logic)
                start_time = time.time()
                
                # Real logic placeholder 
                import random
                sleep_time = random.uniform(0.5, 1.5)
                time.sleep(sleep_time) 
                
                new_status = 'Healthy'
                if random.random() < 0.1: new_status = 'Suspended'
                elif random.random() < 0.05: new_status = 'Locked'
                elif random.random() < 0.05: new_status = 'Invalid Cookies'
                
                # Update DB
                account.health_status = new_status
                account.last_health_check = datetime.datetime.utcnow()
                
                # Log
                duration = int((time.time() - start_time) * 1000)
                log = CheckLog(
                    account_id=account.id,
                    status=new_status,
                    response_time=duration
                )
                db.session.add(log)
                db.session.commit()
                
                return {
                    'id': account.id,
                    'status': new_status,
                    'last_check': account.last_health_check.strftime('%Y-%m-%d %H:%M')
                }
            except Exception as e:
                print(f"Error checking {account_id}: {e}")
                return None

    # Run in parallel
    results = []
    # Limit workers to avoid freezing DB
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(check_single_account, uid) for uid in account_ids]
        for future in futures:
            res = future.result()
            if res: results.append(res)
            
    return jsonify({
        'status': 'success',
        'results': results
    })


@app.route('/api/health/stats/history')
def api_health_stats_history():
    """Get historical health stats for charts"""
    # Last 7 days trend
    today = datetime.datetime.utcnow().date()
    trend_data = []
    
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        next_day = day + datetime.timedelta(days=1)
        
        healthy_count = CheckLog.query.filter(
            CheckLog.timestamp >= day,
            CheckLog.timestamp < next_day,
            CheckLog.status == 'Healthy'
        ).count()
        
        issues_count = CheckLog.query.filter(
            CheckLog.timestamp >= day,
            CheckLog.timestamp < next_day,
            CheckLog.status.in_(['Suspended', 'Locked', 'Invalid Cookies'])
        ).count()
        
        # Format date for Chart.js
        trend_data.append({
            'date': day.strftime('%Y-%m-%d'),
            'healthy': healthy_count,
            'issues': issues_count
        })
        
    return jsonify({
        'status': 'success',
        'trend': trend_data
    })


@app.route('/api/health/export_report')
def api_health_export_report():
    """Export Health Report as CSV"""
    import io
    import csv
    
    logs = CheckLog.query.order_by(CheckLog.timestamp.desc()).limit(1000).all()
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['Account', 'Status', 'Response Time (ms)', 'Date'])
    writer.writeheader()
    
    for log in logs:
        writer.writerow({
            'Account': log.account.username if log.account else 'Unknown',
            'Status': log.status,
            'Response Time (ms)': log.response_time,
            'Date': log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    response = app.response_class(
        response=output.getvalue(),
        status=200,
        mimetype='text/csv'
    )
    response.headers['Content-Disposition'] = f'attachment; filename=health_report_{datetime.datetime.now().strftime("%Y%m%d")}.csv'
    return response


@app.route('/api/health/recommendations')
def api_health_recommendations():
    """Get smart recommendations based on health stats"""
    recommendations = []
    
    total = Account.query.count()
    if total == 0:
        return jsonify({'recommendations': []})
        
    # Stats
    suspended = Account.query.filter(Account.health_status.in_(['Suspended', 'Locked'])).count()
    suspension_rate = (suspended / total) * 100
    
    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    outdated = Account.query.filter((Account.last_health_check < week_ago) | (Account.last_health_check == None)).count()
    
    # Rule 1: High Suspension Rate
    if suspension_rate > 20:
        recommendations.append({
            'type': 'critical',
            'icon': 'fa-radiation',
            'title': 'معدل حظر مرتفع جداً',
            'message': f'نسبة الحظر {int(suspension_rate)}% تشير إلى مشكلة في البروكسيات أو نمط النشر. يوصى بإيقاف الحملات مؤقتاً.',
            'action': None
        })
    elif suspension_rate > 10:
        recommendations.append({
            'type': 'warning',
            'icon': 'fa-exclamation-triangle',
            'title': 'تنبيه جودة الحسابات',
            'message': 'هناك عدد ملحوظ من الحسابات المقفلة. حاول استخدام بروكسيات سكنية (Residential) لتحسين النتائج.',
            'action': None
        })
        
    # Rule 2: Outdated Checks
    if outdated > (total * 0.5) and total > 0:
         recommendations.append({
            'type': 'info',
            'icon': 'fa-history',
            'title': 'تحديث البيانات مطلوب',
            'message': f'أكثر من نصف الحسابات لم يتم فحصها منذ أسبوع. قم بتشغيل "فحص الكل" للحصول على تقارير دقيقة.',
            'action': 'check_all'
        })
        
    # Rule 3: Perfect Health
    if suspension_rate == 0 and outdated == 0 and total > 0:
         recommendations.append({
            'type': 'success',
            'icon': 'fa-shield-alt',
            'title': 'حالة مثالية',
            'message': 'جميع الحسابات سليمة وتم فحصها حديثاً. عمل رائع!',
            'action': None
        })
    
    # Fallback if no specific issues
    if not recommendations and total > 0:
        recommendations.append({
            'type': 'info',
            'icon': 'fa-lightbulb',
            'title': 'نصيحة اليوم',
            'message': 'قم بتوزيع عمليات النشر على مدار اليوم لتجنب لفت انتباه خوارزميات تويتر.',
            'action': None
        })

    return jsonify({'recommendations': recommendations})



@app.route('/add_account', methods=['POST'])
def add_account():
    username = request.form.get('username')
    cookies = request.form.get('cookies')
    proxy = request.form.get('proxy')
    
    existing_account = Account.query.filter_by(username=username).first()
    
    if existing_account:
        existing_account.cookies = cookies
        existing_account.proxy = proxy
        try:
            db.session.commit()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'success', 'message': 'تم تحديث بيانات الحساب بنجاح'})
            return "تم تحديث بيانات الحساب بنجاح <a href='/accounts'>العودة</a>"
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'error', 'message': str(e)})
            return f"خطأ: {str(e)}", 500
    else:
        new_account = Account(username=username, proxy=proxy, cookies=cookies)
        db.session.add(new_account)
        try:
            db.session.commit()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'success', 'message': 'تم إضافة الحساب بنجاح'})
            return "تم إضافة الحساب بنجاح <a href='/accounts'>العودة</a>"
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'error', 'message': str(e)})
            return f"خطأ: {str(e)}", 500

@app.route('/update_account/<int:account_id>', methods=['POST'])
def update_account(account_id):
    account = Account.query.get_or_404(account_id)
    
    # Update fields if present in form
    if 'username' in request.form:
        account.username = request.form.get('username')
    if 'proxy' in request.form:
        account.proxy = request.form.get('proxy')
    if 'cookies' in request.form:
        account.cookies = request.form.get('cookies')
    if 'status' in request.form:
        account.status = request.form.get('status')
        
    try:
        db.session.commit()
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             return jsonify({'status': 'success', 'message': 'تم تحديث الحساب بنجاح'})
        return redirect(url_for('accounts'))
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             return jsonify({'status': 'error', 'message': str(e)})
        return f"خطأ في تحديث الحساب: {str(e)}", 500

@app.route('/get_account_details/<int:account_id>')
def get_account_details(account_id):
    account = Account.query.get_or_404(account_id)
    return jsonify({
        'status': 'success',
        'account': {
            'id': account.id,
            'username': account.username,
            'status': account.status,
            'proxy': account.proxy,
            'cookies': account.cookies,
            'likes_count': account.likes_count,
            'retweets_count': account.retweets_count,
            'last_active': account.last_active.strftime('%Y-%m-%d %H:%M') if account.last_active else '-'
        }
    })

@app.route('/delete_account/<int:account_id>')
def delete_account(account_id):
    account = Account.query.get_or_404(account_id)
    
    # Optional: Delete associated logs first if not using cascade delete
    ActionLog.query.filter_by(account_id=account.id).delete()
    
    db.session.delete(account)
    db.session.commit()
    return redirect(url_for('accounts'))



@app.route('/update_account_stats/<int:account_id>', methods=['POST'])
def update_account_stats(account_id):
    account = Account.query.get_or_404(account_id)
    try:
        # Recalculate stats from Action Logs
        likes = ActionLog.query.filter_by(account_id=account.id, action_type='like', status='Success').count()
        # Also count 'both' if any
        both_likes = ActionLog.query.filter_by(account_id=account.id, action_type='both', status='Success').count()
        
        retweets = ActionLog.query.filter_by(account_id=account.id, action_type='retweet', status='Success').count()
        both_retweets = ActionLog.query.filter_by(account_id=account.id, action_type='both', status='Success').count()
        
        account.likes_count = likes + both_likes
        account.retweets_count = retweets + both_retweets
        
        # Update last active if strictly needed, but might override real last activity
        # account.last_active = datetime.datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'message': 'تم تحديث الإحصائيات بنجاح',
            'likes': account.likes_count,
            'retweets': account.retweets_count,
            'last_active': account.last_active.strftime('%Y-%m-%d') if account.last_active else '-'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/test_proxy', methods=['POST'])
def test_proxy():
    data = request.json
    proxy = data.get('proxy')
    
    if not proxy:
        return jsonify({'status': 'error', 'message': 'الرجاء إدخال البروكسي'})

    try:
        # Simple proxy test logic
        proxies = {
            "http": proxy,
            "https": proxy,
        }
        # Timeout is short to keep UI responsive
        response = requests.get("http://www.google.com", proxies=proxies, timeout=5)
        
        if response.status_code == 200:
            return jsonify({'status': 'success', 'message': 'تم الاتصال بالبروكسي بنجاح'})
        else:
            return jsonify({'status': 'error', 'message': f'فشل الاتصال: رمز الحالة {response.status_code}'})
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'فشل الاتصال: {str(e)}'})




@app.route('/delete_accounts_bulk', methods=['POST'])
def delete_accounts_bulk():
    data = request.json
    account_ids = data.get('ids', [])
    
    if not account_ids:
        return jsonify({'status': 'error', 'message': 'No accounts selected'})
        
    try:
        # Delete related logs first
        ActionLog.query.filter(ActionLog.account_id.in_(account_ids)).delete(synchronize_session=False)
        
        # Delete accounts
        Account.query.filter(Account.id.in_(account_ids)).delete(synchronize_session=False)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': f'تم حذف {len(account_ids)} حساب بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/check_accounts_bulk', methods=['POST'])
def check_accounts_bulk():
    data = request.json
    account_ids = data.get('ids', [])
    
    if not account_ids:
        return jsonify({'status': 'error', 'message': 'No accounts selected'})
    
    # Needs to be async ideally, but for now we iterate (slow)
    from core.browser import TwitterBot
    
    results = []
    bot = TwitterBot(headless=True)
    try:
        bot.start_browser()
        
        accounts = Account.query.filter(Account.id.in_(account_ids)).all()
        for acc in accounts:
            try:
                status = bot.check_account_status(acc.username, acc.cookies) # Assuming check_account_status doesn't need re-init
                acc.health_status = status
                acc.last_health_check = datetime.datetime.utcnow()
                
                # Simple status mapping
                if status == 'Valid':
                    acc.status = 'Active'
                elif status in ['Suspended', 'Locked']:
                    acc.status = status
                    
                results.append({'id': acc.id, 'status': status})
            except Exception as e:
                results.append({'id': acc.id, 'status': 'Error', 'error': str(e)})
                
        db.session.commit()
        return jsonify({'status': 'success', 'results': results})
        
    except Exception as e:
         return jsonify({'status': 'error', 'message': str(e)})
    finally:
        bot.close()


@app.route('/support')
def support():
    tasks = SupportTask.query.order_by(SupportTask.created_at.desc()).limit(20).all()
    
    # Calculate Stats
    total_tasks = SupportTask.query.count()
    completed_tasks = SupportTask.query.filter_by(status='Completed').count()
    active_tasks = SupportTask.query.filter(SupportTask.status.in_(['Pending', 'In Progress'])).count()
    total_actions_performed = db.session.query(db.func.sum(SupportTask.completed_count)).scalar() or 0
    
    return render_template('support.html', 
                          tasks=tasks,
                          total_tasks=total_tasks,
                          completed_tasks=completed_tasks,
                          active_tasks=active_tasks,
                          total_actions_performed=int(total_actions_performed))

@app.route('/create_task', methods=['POST'])
def create_task():
    target_url = request.form.get('target_url')
    # Simple validation
    if not target_url:
        return "Target URL is required", 400
        
    task_type = request.form.get('task_type')
    target_count = int(request.form.get('target_count', 10))
    execution_time_str = request.form.get('execution_time')
    
    scheduled_time = datetime.datetime.utcnow()
    if execution_time_str:
        try:
            # Browser datetime-local sends ISO format usually
            scheduled_time = datetime.datetime.strptime(execution_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            pass # Fallback to now if parse fails

    new_task = SupportTask(
        target_url=target_url,
        task_type=task_type,
        target_count=target_count,
        scheduled_time=scheduled_time
    )
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('support'))

# ==========================================
# Task Management & Templates API
# ==========================================

@app.route('/api/tasks/list')
def api_tasks_list():
    """Get tasks with filtering and search"""
    status_filter = request.args.get('status')
    type_filter = request.args.get('type')
    search_query = request.args.get('search')
    
    query = SupportTask.query.filter_by(visible=True)
    
    if status_filter and status_filter != 'all':
        query = query.filter_by(status=status_filter)
        
    if type_filter and type_filter != 'all':
        query = query.filter_by(task_type=type_filter)
        
    if search_query:
        query = query.filter(SupportTask.target_url.contains(search_query))
        
    tasks = query.order_by(SupportTask.created_at.desc()).limit(50).all()
    
    tasks_data = []
    for t in tasks:
        tasks_data.append({
            'id': t.id,
            'target_url': t.target_url,
            'task_type': t.task_type,
            'status': t.status,
            'completed_count': t.completed_count,
            'target_count': t.target_count,
            'progress': int((t.completed_count / t.target_count) * 100) if t.target_count > 0 else 0,
            'is_paused': t.is_paused,
            'scheduled_time': t.scheduled_time.strftime('%Y-%m-%d %H:%M') if t.scheduled_time else ''
        })
        
    return jsonify({'tasks': tasks_data})

@app.route('/api/tasks/action', methods=['POST'])
def api_tasks_action():
    """Handle task actions: pause, resume, delete, retry"""
    data = request.json
    action = data.get('action')
    task_id = data.get('task_id')
    
    task = SupportTask.query.get_or_404(task_id)
    
    if action == 'pause':
        task.status = 'Paused'
        task.is_paused = True
    elif action == 'resume':
        task.status = 'In Progress'
        task.is_paused = False
    elif action == 'delete':
        task.visible = False # Soft delete
    elif action == 'retry':
        task.status = 'Pending'
        task.is_paused = False
        task.completed_count = 0 
        
    db.session.commit()
    return jsonify({'status': 'success', 'new_status': task.status})

@app.route('/api/templates/save', methods=['POST'])
def api_save_template():
    data = request.json
    new_template = TaskTemplate(
        name=data.get('name'),
        target_url=data.get('target_url'),
        task_type=data.get('task_type'),
        target_count=data.get('target_count')
    )
    db.session.add(new_template)
    db.session.commit()
    return jsonify({'status': 'success', 'id': new_template.id})

@app.route('/api/templates/list')
def api_list_templates():
    templates = TaskTemplate.query.order_by(TaskTemplate.created_at.desc()).all()
    return jsonify({'templates': [{
        'id': t.id,
        'name': t.name,
        'target_url': t.target_url,
        'task_type': t.task_type,
        'target_count': t.target_count
    } for t in templates]})

@app.route('/api/tasks/edit/<int:task_id>', methods=['POST'])
def api_task_edit(task_id):
    """تحرير مهمة موجودة"""
    task = SupportTask.query.get_or_404(task_id)
    data = request.json
    
    # Update allowed fields
    if 'target_url' in data:
        task.target_url = data['target_url']
    if 'task_type' in data:
        task.task_type = data['task_type']
    if 'target_count' in data:
        task.target_count = int(data['target_count'])
    if 'scheduled_time' in data:
        try:
            task.scheduled_time = datetime.datetime.strptime(data['scheduled_time'], '%Y-%m-%dT%H:%M')
        except:
            pass
    
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'تم تحديث المهمة بنجاح'})

@app.route('/api/tasks/details/<int:task_id>')
def api_task_details(task_id):
    """جلب التفاصيل الموسعة لمهمة"""
    task = SupportTask.query.get_or_404(task_id)
    
    # Parse JSON fields
    accounts_used = []
    if task.accounts_used:
        try:
            account_ids = json.loads(task.accounts_used)
            for acc_id in account_ids:
                acc = Account.query.get(acc_id)
                if acc:
                    accounts_used.append({
                        'id': acc.id,
                        'username': acc.username,
                        'status': acc.status
                    })
        except:
            pass
    
    # Parse detailed log
    detailed_log = task.detailed_log or 'لا يوجد سجل مفصل'
    
    # Parse error log
    error_log = []
    if task.error_log:
        try:
            error_log = json.loads(task.error_log)
        except:
            error_log = [task.error_log]
    
    return jsonify({
        'status': 'success',
        'task': {
            'id': task.id,
            'target_url': task.target_url,
            'task_type': task.task_type,
            'status': task.status,
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'scheduled_time': task.scheduled_time.strftime('%Y-%m-%d %H:%M:%S') if task.scheduled_time else '',
            'completed_count': task.completed_count,
            'target_count': task.target_count
        },
        'accounts_used': accounts_used,
        'detailed_log': detailed_log,
        'error_log': error_log,
        'last_error': task.last_error or 'لا توجد أخطاء'
    })

@app.route('/api/tasks/stop/<int:task_id>', methods=['POST'])
def api_task_stop(task_id):
    """إيقاف نهائي للمهمة (مختلف عن pause)"""
    task = SupportTask.query.get_or_404(task_id)
    task.status = 'Failed'
    task.is_paused = True
    task.last_error = 'تم إيقاف المهمة بشكل نهائي من قبل المستخدم'
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'تم إيقاف المهمة نهائياً'})



# ==========================================
# Saved Filters API
# ==========================================

@app.route('/api/filters/save', methods=['POST'])
def api_save_filter():
    """حفظ فلتر مخصص"""
    data = request.json
    new_filter = SavedFilter(
        name=data.get('name'),
        filter_data=json.dumps({
            'status': data.get('status'),
            'type': data.get('type'),
            'search': data.get('search', '')
        }),
        is_default=data.get('is_default', False)
    )
    
    # If this is marked as default, unset others
    if new_filter.is_default:
        SavedFilter.query.update({'is_default': False})
    
    db.session.add(new_filter)
    db.session.commit()
    return jsonify({'status': 'success', 'id': new_filter.id})

@app.route('/api/filters/list')
def api_list_filters():
    """جلب الفلاتر المحفوظة"""
    filters = SavedFilter.query.order_by(SavedFilter.created_at.desc()).all()
    return jsonify({'filters': [{
        'id': f.id,
        'name': f.name,
        'filter_data': json.loads(f.filter_data),
        'is_default': f.is_default
    } for f in filters]})

@app.route('/api/filters/delete/<int:filter_id>', methods=['DELETE'])
def api_delete_filter(filter_id):
    """حذف فلتر محفوظ"""
    saved_filter = SavedFilter.query.get_or_404(filter_id)
    db.session.delete(saved_filter)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'تم حذف الفلتر بنجاح'})

# ==========================================
# Advanced Template Management
# ==========================================

@app.route('/api/templates/update/<int:template_id>', methods=['PUT'])
def api_update_template(template_id):
    """تحديث قالب موجود"""
    template = TaskTemplate.query.get_or_404(template_id)
    data = request.json
    
    if 'name' in data:
        template.name = data['name']
    if 'target_url' in data:
        template.target_url = data['target_url']
    if 'task_type' in data:
        template.task_type = data['task_type']
    if 'target_count' in data:
        template.target_count = data['target_count']
    
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'تم تحديث القالب بنجاح'})

@app.route('/api/templates/delete/<int:template_id>', methods=['DELETE'])
def api_delete_template(template_id):
    """حذف قالب"""
    template = TaskTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'تم حذف القالب بنجاح'})

# ==========================================
# Notifications API
# ==========================================

@app.route('/api/notifications/settings', methods=['GET', 'POST'])
def api_notification_settings():
    """حفظ/جلب إعدادات الإشعارات"""
    if request.method == 'POST':
        data = request.json
        
        # Get or create settings (only one row should exist)
        settings = NotificationSettings.query.first()
        if not settings:
            settings = NotificationSettings()
            db.session.add(settings)
        
        # Update settings
        if 'browser_enabled' in data:
            settings.browser_enabled = data['browser_enabled']
        if 'email_enabled' in data:
            settings.email_enabled = data['email_enabled']
        if 'email_address' in data:
            settings.email_address = data['email_address']
        if 'telegram_enabled' in data:
            settings.telegram_enabled = data['telegram_enabled']
        if 'telegram_chat_id' in data:
            settings.telegram_chat_id = data['telegram_chat_id']
        if 'notify_on_complete' in data:
            settings.notify_on_complete = data['notify_on_complete']
        if 'notify_on_fail' in data:
            settings.notify_on_fail = data['notify_on_fail']
        if 'notify_on_pause' in data:
            settings.notify_on_pause = data['notify_on_pause']
        
        settings.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'تم حفظ الإعدادات بنجاح'})
    
    else:  # GET
        settings = NotificationSettings.query.first()
        if not settings:
            return jsonify({
                'browser_enabled': True,
                'email_enabled': False,
                'email_address': '',
                'telegram_enabled': False,
                'telegram_chat_id': '',
                'notify_on_complete': True,
                'notify_on_fail': True,
                'notify_on_pause': False
            })
        
        return jsonify({
            'browser_enabled': settings.browser_enabled,
            'email_enabled': settings.email_enabled,
            'email_address': settings.email_address or '',
            'telegram_enabled': settings.telegram_enabled,
            'telegram_chat_id': settings.telegram_chat_id or '',
            'notify_on_complete': settings.notify_on_complete,
            'notify_on_fail': settings.notify_on_fail,
            'notify_on_pause': settings.notify_on_pause
        })

@app.route('/api/notifications/test', methods=['POST'])
def api_test_notification():
    """اختبار إرسال إشعار"""
    data = request.json
    notification_type = data.get('type', 'email')  # email or telegram
    
    settings = NotificationSettings.query.first()
    if not settings:
        return jsonify({'status': 'error', 'message': 'لم يتم إعداد الإشعارات بعد'})
    
    try:
        if notification_type == 'email':
            if not settings.email_enabled or not settings.email_address:
                return jsonify({'status': 'error', 'message': 'البريد الإلكتروني غير مفعل أو لم يتم تحديد عنوان'})
            
            # TODO: Implement email sending using SMTP
            # This would require SMTP settings from Settings model
            return jsonify({'status': 'info', 'message': 'إرسال البريد غير مفعّل حالياً. يتطلب إعدادات SMTP'})
        
        elif notification_type == 'telegram':
            if not settings.telegram_enabled or not settings.telegram_chat_id:
                return jsonify({'status': 'error', 'message': 'Telegram غير مفعل أو لم يتم تحديد Chat ID'})
            
            # TODO: Implement Telegram sending
            # This would require telegram bot token from Settings model
            return jsonify({'status': 'info', 'message': 'إرسال Telegram غير مفعّل حالياً. يتطلب Bot Token'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# Health Clinic Routes
@app.route('/health')
def health():
    accounts = Account.query.all()
    # Calculate simple stats
    healthy = sum(1 for a in accounts if a.health_status == 'Healthy')
    issues = sum(1 for a in accounts if a.health_status in ['Suspended', 'Locked', 'Invalid Cookies'])
    return render_template('health.html', accounts=accounts, healthy=healthy, issues=issues)

@app.route('/check_health/<int:account_id>', methods=['POST'])
def check_health(account_id):
    account = Account.query.get_or_404(account_id)
    
    # We run this synchronously for immediate feedback, or should we use background?
    # For a single account, sync might be okay if user accepts delay (30s+).
    # Ideally async, but for MVP let's do sync with loading state.
    
    from core.browser import TwitterBot
    bot = TwitterBot(headless=True) # Use headless
    try:
        print(f"Checking health for {account.username}...")
        bot.start_browser(proxy=account.proxy, user_agent=account.user_agent)
        
        status = bot.check_account_status(account.username, account.cookies)
        
        # Fetch Profile Details if Healthy
        if status == 'Healthy':
             try:
                 d_name, p_img = bot.get_profile_details(account.username)
                 if d_name: account.display_name = d_name
                 if p_img: account.profile_image_url = p_img
             except Exception as e:
                 print(f"Failed to fetch details: {e}")

        account.health_status = status
        account.last_health_check = datetime.datetime.utcnow()
        db.session.commit()
        
        msg = f"Account status: {status}"
        return jsonify({'status': 'success', 'health': status, 'message': msg})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        bot.close()



# Settings Routes
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    # Get or Create default settings
    settings = Settings.query.first()
    if not settings:
        settings = Settings(app_name='X-Boost Pro', ai_provider='groq', ai_model='llama-3.1-8b-instant', ai_system_prompt='أنت مستخدم تويتر ذكي ولطيف. رد على التغريدة باللهجة البيضاء أو السعودية بشكل مختصر وجذاب.')
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        settings.ai_provider = request.form.get('ai_provider')
        settings.ai_api_key = request.form.get('ai_api_key')
        
        # Auto-correct old model if user submits it
        submitted_model = request.form.get('ai_model')
        if submitted_model == 'llama3-8b-8192':
            submitted_model = 'llama-3.1-8b-instant'
        settings.ai_model = submitted_model
        
        settings.ai_system_prompt = request.form.get('ai_system_prompt')
        db.session.commit()
        return render_template('settings.html', settings=settings, message="تم حفظ الإعدادات بنجاح ✅")

    # Auto-correct on load if needed
    if settings.ai_model == 'llama3-8b-8192':
        settings.ai_model = 'llama-3.1-8b-instant'
        db.session.commit()

    return render_template('settings.html', settings=settings)

@app.route('/test_ai', methods=['POST'])
def test_ai():
    settings = Settings.query.first()
    if not settings or not settings.ai_api_key:
        return jsonify({'status': 'error', 'message': 'API Key not configured'})
    
    # Final safety check before usage
    model_to_use = settings.ai_model
    if model_to_use == 'llama3-8b-8192':
        model_to_use = 'llama-3.1-8b-instant'
        settings.ai_model = model_to_use
        db.session.commit()
        
    from core.ai_client import AIGenerator
    ai = AIGenerator(
        api_key=settings.ai_api_key, 
        provider=settings.ai_provider, 
        model=model_to_use,
        system_prompt=settings.ai_system_prompt
    )
    
    reply = ai.generate_reply("This is a test tweet about technology.")
    return jsonify({'status': 'success', 'reply': reply})

# Auto Support Routes
@app.route('/auto_support')
def auto_support():
    accounts = MonitoredAccount.query.all()
    
    # Calculate dynamic stats for each account (since we can't easily alter DB schema)
    for account in accounts:
        # Count replies targeting this account's username
        account.stats_replies = ActionLog.query.filter(
            ActionLog.action_type == 'reply',
            ActionLog.target.contains(account.username)
        ).count()
    
    today = datetime.datetime.now(datetime.UTC).date()
    # Ensure timezone awareness for consistent comparison
    today_start = datetime.datetime(today.year, today.month, today.day, tzinfo=datetime.timezone.utc)
    yesterday_start = today_start - datetime.timedelta(days=1)
    week_start = today_start - datetime.timedelta(days=7)

    # Enhanced Stats with Time Periods
    # Today's Stats
    today_likes = ActionLog.query.filter(
        ActionLog.action_type == 'like',
        ActionLog.status == 'Success',
        ActionLog.timestamp >= today_start
    ).count()
    today_retweets = ActionLog.query.filter(
        ActionLog.action_type == 'retweet',
        ActionLog.status == 'Success',
        ActionLog.timestamp >= today_start
    ).count()
    today_replies = ActionLog.query.filter(
        ActionLog.action_type == 'reply',
        ActionLog.status == 'Success',
        ActionLog.timestamp >= today_start
    ).count()
    today_ops = today_likes + today_retweets + today_replies

    # Yesterday's Stats for Comparison
    yesterday_likes = ActionLog.query.filter(
        ActionLog.action_type == 'like',
        ActionLog.status == 'Success',
        ActionLog.timestamp >= yesterday_start,
        ActionLog.timestamp < today_start
    ).count()
    yesterday_retweets = ActionLog.query.filter(
        ActionLog.action_type == 'retweet',
        ActionLog.status == 'Success',
        ActionLog.timestamp >= yesterday_start,
        ActionLog.timestamp < today_start
    ).count()
    yesterday_replies = ActionLog.query.filter(
        ActionLog.action_type == 'reply',
        ActionLog.status == 'Success',
        ActionLog.timestamp >= yesterday_start,
        ActionLog.timestamp < today_start
    ).count()
    yesterday_ops = yesterday_likes + yesterday_retweets + yesterday_replies

    # Week Stats
    week_likes = ActionLog.query.filter(
        ActionLog.action_type == 'like',
        ActionLog.status == 'Success',
        ActionLog.timestamp >= week_start
    ).count()
    week_retweets = ActionLog.query.filter(
        ActionLog.action_type == 'retweet',
        ActionLog.status == 'Success',
        ActionLog.timestamp >= week_start
    ).count()
    week_replies = ActionLog.query.filter(
        ActionLog.action_type == 'reply',
        ActionLog.status == 'Success',
        ActionLog.timestamp >= week_start
    ).count()
    week_ops = week_likes + week_retweets + week_replies

    # Global Stats (All Time)
    # Global Stats (All Time)
    success_logs = ActionLog.query.filter_by(status='Success')
    
    total_likes = success_logs.filter((ActionLog.action_type == 'like') | (ActionLog.action_type == 'both')).count()
    total_retweets = success_logs.filter((ActionLog.action_type == 'retweet') | (ActionLog.action_type == 'both')).count()
    total_replies = success_logs.filter_by(action_type='reply').count()
    
    # Total Ops is simply the count of successful logs (each log is one operation cycle)
    total_ops = success_logs.count()

    # Hourly Activity for Today (for chart)
    hourly_activity = []
    for hour in range(24):
        hour_start = today_start + datetime.timedelta(hours=hour)
        hour_end = hour_start + datetime.timedelta(hours=1)
        
        hour_ops = ActionLog.query.filter(
            ActionLog.timestamp >= hour_start,
            ActionLog.timestamp < hour_end,
            ActionLog.status == 'Success'
        ).count()
        
        hourly_activity.append(hour_ops)

    # Recent Activity (Global)
    recent_logs = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(15).all()

    # Calculate growth percentages
    daily_growth = ((today_ops - yesterday_ops) / yesterday_ops * 100) if yesterday_ops > 0 else 0
    weekly_avg = week_ops / 7 if week_ops > 0 else 0
    
    print(f"DEBUG STATS: Likes={total_likes}, Retweets={total_retweets}, Replies={total_replies}, Ops={total_ops}")

    return render_template('auto_support.html', 
                          accounts=accounts,
                          # Today's Stats
                          today_likes=today_likes,
                          today_retweets=today_retweets,
                          today_replies=today_replies,
                          today_ops=today_ops,
                          # Yesterday's Stats
                          yesterday_likes=yesterday_likes,
                          yesterday_retweets=yesterday_retweets,
                          yesterday_replies=yesterday_replies,
                          yesterday_ops=yesterday_ops,
                          # Week Stats
                          week_likes=week_likes,
                          week_retweets=week_retweets,
                          week_replies=week_replies,
                          week_ops=week_ops,
                          # Global Stats
                          total_likes=total_likes,
                          total_retweets=total_retweets,
                          total_replies=total_replies,
                          total_ops=total_ops,
                          # Additional Data
                          hourly_activity=hourly_activity,
                          daily_growth=daily_growth,
                          weekly_avg=weekly_avg,
                          recent_logs=recent_logs)

@app.route('/add_monitored_account', methods=['POST'])
def add_monitored_account():
    username = request.form.get('username')
    # Strip @ if present
    username = username.replace('@', '').strip()
    
    # task_type is now a list of checkboxes
    task_types_list = request.form.getlist('task_type')
    if not task_types_list:
        task_type = 'like' # Default
    else:
        task_type = ','.join(task_types_list)
        
    check_interval = int(request.form.get('check_interval', 5))
    
    existing = MonitoredAccount.query.filter_by(username=username).first()
    if existing:
        # Update existing
        existing.task_type = task_type
        existing.check_interval = check_interval
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'تم تحديث إعدادات الحساب بنجاح'})
    
    new_account = MonitoredAccount(
        username=username,
        task_type=task_type,
        check_interval=check_interval
    )
    db.session.add(new_account)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'تم إضافة الحساب للمراقبة بنجاح'})

@app.route('/toggle_monitor/<int:account_id>')
def toggle_monitor(account_id):
    account = MonitoredAccount.query.get_or_404(account_id)
    account.is_active = not account.is_active
    db.session.commit()
    return redirect(url_for('auto_support'))

@app.route('/delete_monitored_account/<int:account_id>')
def delete_monitored_account(account_id):
    account = MonitoredAccount.query.get_or_404(account_id)
    db.session.delete(account)
    db.session.commit()
    return redirect(url_for('auto_support'))

@app.route('/force_check_account/<int:account_id>')
def force_check_account(account_id):
    account = MonitoredAccount.query.get_or_404(account_id)
    
    # We need to temporarily instantiate a bot or reuse engine logic
    # Since engine runs in background, we might want to be careful.
    # But for a single check, spinning up a headless bot is fine.
    
    from core.browser import TwitterBot
    from flask import current_app
    from models import Account # Assuming Account model is needed for proxy/user_agent
    
    # We need a bot instance
    bot = TwitterBot(headless=True)
    try:
        # Use active account proxy if available
        active_acc = Account.query.filter_by(status='Active').first()
        if active_acc:
             bot.start_browser(proxy=active_acc.proxy, user_agent=active_acc.user_agent)
             if active_acc.cookies: bot.load_cookies(active_acc.cookies)
        else:
             bot.start_browser()
             
        # Access engine via current_app instance
        current_app.support_engine.process_monitored_account(account, bot)
        
    except Exception as e:
        return f"Error checking account: {str(e)}", 500
    finally:
        bot.close()
        
    return redirect(url_for('auto_support'))


@app.route('/api/recent_logs')
def api_recent_logs():
    logs = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(20).all()
    logs_data = []
    for log in logs:
        # Get username safely
        username = log.account.username if log.account else 'Unknown'
        
        logs_data.append({
            'id': log.id,
            'timestamp': log.timestamp.strftime('%H:%M:%S'),
            'action_type': log.action_type,
            'target': log.target,
            'status': log.status,
            'username': username,
            'details': log.details
        })
    return jsonify({'status': 'success', 'logs': logs_data})


# ===== Dashboard API Endpoints =====

@app.route('/api/dashboard/stats')
def api_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    total_accounts = Account.query.count()
    active_accounts = Account.query.filter_by(status='Active').count()
    total_actions = ActionLog.query.count()
    pending_tasks = SupportTask.query.filter_by(status='Pending').count()
    
    # Success rate
    success_count = ActionLog.query.filter_by(status='Success').count()
    success_rate = round((success_count / total_actions * 100) if total_actions > 0 else 0)
    
    # Calculate percentages for progress bars
    accounts_percentage = round((active_accounts / total_accounts * 100) if total_accounts > 0 else 0)
    
    # Trends (compare with yesterday)
    today = datetime.datetime.utcnow().date()
    today_start = datetime.datetime(today.year, today.month, today.day)
    yesterday_start = today_start - datetime.timedelta(days=1)
    
    today_actions = ActionLog.query.filter(ActionLog.timestamp >= today_start).count()
    yesterday_actions = ActionLog.query.filter(
        ActionLog.timestamp >= yesterday_start,
        ActionLog.timestamp < today_start
    ).count()
    
    actions_trend = round(((today_actions - yesterday_actions) / yesterday_actions * 100) if yesterday_actions > 0 else 0)
    
    return jsonify({
        'active_accounts': active_accounts,
        'total_actions': total_actions,
        'pending_tasks': pending_tasks,
        'success_rate': success_rate,
        'accounts_percentage': accounts_percentage,
        'actions_percentage': min(100, today_actions),  # Cap at 100
        'pending_percentage': min(100, pending_tasks * 10),
        'accounts_trend': 0,  # Would need historical data
        'actions_trend': actions_trend,
        'success_trend': 0
    })


@app.route('/api/dashboard/charts')
def api_dashboard_charts():
    """Get chart data for dashboard"""
    # Accounts distribution
    active = Account.query.filter_by(status='Active').count()
    suspended = Account.query.filter(Account.status.in_(['Suspended', 'Locked'])).count()
    other = Account.query.filter(~Account.status.in_(['Active', 'Suspended', 'Locked'])).count()
    
    # Daily activity (last 7 days)
    daily_activity = []
    today = datetime.datetime.utcnow().date()
    
    for i in range(6, -1, -1):
        day_start = datetime.datetime(today.year, today.month, today.day) - datetime.timedelta(days=i)
        day_end = day_start + datetime.timedelta(days=1)
        
        count = ActionLog.query.filter(
            ActionLog.timestamp >= day_start,
            ActionLog.timestamp < day_end
        ).count()
        daily_activity.append(count)
    
    # Tasks status
    completed = SupportTask.query.filter_by(status='Completed').count()
    in_progress = SupportTask.query.filter_by(status='In Progress').count()
    pending = SupportTask.query.filter_by(status='Pending').count()
    failed = SupportTask.query.filter_by(status='Failed').count()
    
    return jsonify({
        'accounts': {
            'active': active,
            'suspended': suspended,
            'locked': other
        },
        'daily_activity': daily_activity,
        'tasks': {
            'completed': completed,
            'in_progress': in_progress,
            'pending': pending,
            'failed': failed
        }
    })


@app.route('/api/dashboard/alerts')
def api_dashboard_alerts():
    """Get active alerts for dashboard"""
    alerts = []
    
    # Suspended accounts
    suspended_count = Account.query.filter(Account.status.in_(['Suspended', 'Locked'])).count()
    if suspended_count > 0:
        alerts.append({
            'type': 'danger',
            'title': 'حسابات معلقة',
            'message': f'يوجد {suspended_count} حساب معلق أو مقفل',
            'time': ''
        })
    
    # Failed tasks
    failed_tasks = SupportTask.query.filter_by(status='Failed').count()
    if failed_tasks > 0:
        alerts.append({
            'type': 'warning',
            'title': 'مهام فاشلة',
            'message': f'يوجد {failed_tasks} مهمة فاشلة تحتاج المراجعة',
            'time': ''
        })
    
    # Health check needed
    one_day_ago = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    unchecked = Account.query.filter(
        (Account.last_health_check == None) | (Account.last_health_check < one_day_ago)
    ).count()
    if unchecked > 0:
        alerts.append({
            'type': 'info',
            'title': 'فحص صحي مطلوب',
            'message': f'{unchecked} حساب يحتاج فحص صحي',
            'time': ''
        })
    
    return jsonify(alerts)


@app.route('/api/dashboard/live-status')
def api_dashboard_live_status():
    """Get live status for dashboard"""
    running_tasks = SupportTask.query.filter_by(status='In Progress').count()
    
    # Active accounts in last 30 minutes
    thirty_min_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
    active_accounts = Account.query.filter(Account.last_active >= thirty_min_ago).count()
    
    # Last activity
    last_log = ActionLog.query.order_by(ActionLog.timestamp.desc()).first()
    if last_log:
        time_diff = datetime.datetime.utcnow() - last_log.timestamp
        minutes = int(time_diff.total_seconds() / 60)
        if minutes < 1:
            last_activity = "الآن"
        elif minutes < 60:
            last_activity = f"منذ {minutes} د"
        else:
            hours = minutes // 60
            last_activity = f"منذ {hours} س"
    else:
        last_activity = "لا يوجد"
    
    return jsonify({
        'running_tasks': running_tasks,
        'active_accounts': active_accounts,
        'last_activity': last_activity
    })


@app.route('/api/dashboard/comparison')
def api_dashboard_comparison():
    """Get comparison statistics for dashboard"""
    today = datetime.datetime.utcnow().date()
    today_start = datetime.datetime(today.year, today.month, today.day)
    
    # Weekly comparison
    week_start = today_start - datetime.timedelta(days=today.weekday())
    week_current = ActionLog.query.filter(ActionLog.timestamp >= week_start).count()
    
    last_week_start = week_start - datetime.timedelta(days=7)
    week_previous = ActionLog.query.filter(
        ActionLog.timestamp >= last_week_start,
        ActionLog.timestamp < week_start
    ).count()
    
    week_change = round(((week_current - week_previous) / week_previous * 100) if week_previous > 0 else 0)
    
    # Monthly comparison
    month_start = datetime.datetime(today.year, today.month, 1)
    month_current = ActionLog.query.filter(ActionLog.timestamp >= month_start).count()
    
    if today.month == 1:
        last_month_start = datetime.datetime(today.year - 1, 12, 1)
    else:
        last_month_start = datetime.datetime(today.year, today.month - 1, 1)
    
    month_previous = ActionLog.query.filter(
        ActionLog.timestamp >= last_month_start,
        ActionLog.timestamp < month_start
    ).count()
    
    month_change = round(((month_current - month_previous) / month_previous * 100) if month_previous > 0 else 0)
    
    return jsonify({
        'week': {
            'current': week_current,
            'previous': week_previous,
            'change': week_change
        },
        'month': {
            'current': month_current,
            'previous': month_previous,
            'change': month_change
        }
    })


# Campaign Routes
@app.route('/campaigns')
def campaigns():
    all_campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    
    total_campaigns = len(all_campaigns)
    active_campaigns = sum(1 for c in all_campaigns if c.status == 'Active')
    completed_campaigns = sum(1 for c in all_campaigns if c.status == 'Completed')
    
    return render_template('campaigns.html', 
                          campaigns=all_campaigns,
                          total_campaigns=total_campaigns,
                          active_campaigns=active_campaigns,
                          completed_campaigns=completed_campaigns)

@app.route('/create_campaign', methods=['POST'])
def create_campaign():
    name = request.form.get('name')
    target_input = request.form.get('target_input')
    target_quantity = int(request.form.get('target_quantity', 10))
    speed = int(request.form.get('speed', 3))
    
    # Actions (Checkbox list)
    actions_list = request.form.getlist('actions')
    if not actions_list:
        actions_list = ['like'] # Default
    
    actions_json = json.dumps(actions_list)
    
    # Determine Campaign Type
    if '/status/' in target_input:
        c_type = 'Tweet'
    elif 'twitter.com' in target_input or '@' in target_input or ' ' not in target_input:
        # Likely a profile URL or username
        c_type = 'Profile'
    else:
        c_type = 'Tweet' # Fallback
        
    # Parse Scheduled Time
    scheduled_str = request.form.get('scheduled_time')
    scheduled_time = None
    status = 'Active'
    
    if scheduled_str:
        try:
            scheduled_time = datetime.datetime.strptime(scheduled_str, '%Y-%m-%dT%H:%M')
            if scheduled_time > datetime.datetime.utcnow():
                status = 'Scheduled'
        except ValueError:
            pass # Invalid format, ignore
            
    new_campaign = Campaign(
        name=name,
        campaign_type=c_type,
        target_input=target_input,
        actions=actions_json,
        target_quantity=target_quantity,
        speed=speed,
        status=status,
        scheduled_time=scheduled_time
    )
    
    db.session.add(new_campaign)
    db.session.commit()
    
    return redirect(url_for('campaigns'))

@app.route('/api/campaign_action/<action>/<int:id>')
def campaign_action(action, id):
    campaign = Campaign.query.get_or_404(id)
    
    if action == 'pause':
        campaign.status = 'Paused'
    elif action == 'resume':
        campaign.status = 'Active'
    elif action == 'delete':
        db.session.delete(campaign)
    
    db.session.commit()
    return jsonify({'status': 'success', 'message': f'Campaign {action}d'})



# --- Proxy Manager Routes ---

@app.route('/proxies')
def proxies():
    all_proxies = Proxy.query.all()
    total = len(all_proxies)
    active = sum(1 for p in all_proxies if p.status == 'Active')
    dead = sum(1 for p in all_proxies if p.status == 'Dead')
    
    return render_template('proxies.html', proxies=all_proxies, 
                         total_proxies=total, active_proxies=active, dead_proxies=dead)

@app.route('/add_proxy', methods=['POST'])
def add_proxy():
    form_type = request.form.get('type', 'bulk')
    
    if form_type == 'bulk':
        raw_list = request.form.get('proxy_list')
        if raw_list:
            lines = raw_list.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # Basic validation/deduplication
                if not Proxy.query.filter_by(proxy_string=line).first():
                    new_proxy = Proxy(proxy_string=line, status='Unknown')
                    db.session.add(new_proxy)
            db.session.commit()
            
    elif form_type == 'single':
        host = request.form.get('host')
        port = request.form.get('port')
        user = request.form.get('user')
        password = request.form.get('pass')
        
        if host and port:
            if user and password:
                p_string = f"{user}:{password}@{host}:{port}"
            else:
                p_string = f"{host}:{port}"
                
            if not Proxy.query.filter_by(proxy_string=p_string).first():
                new_proxy = Proxy(proxy_string=p_string, status='Unknown')
                db.session.add(new_proxy)
                db.session.commit()

    return redirect(url_for('proxies'))

@app.route('/delete_proxy/<int:id>', methods=['DELETE'])
def delete_proxy(id):
    proxy = Proxy.query.get(id)
    if proxy:
        db.session.delete(proxy)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/check_proxy/<int:id>')
def check_proxy_route(id):
    proxy = Proxy.query.get(id)
    if not proxy: 
        return jsonify({'success': False, 'message': 'Not found'})
        
    # Simple Connectivity Check
    import requests
    import time
    
    proxy_url = proxy.proxy_string
    # Format for requests: http://user:pass@host:port or http://host:port
    # Assumes HTTP proxies for now
    if '://' not in proxy_url:
        proxy_dict = {
            "http": f"http://{proxy_url}",
            "https": f"http://{proxy_url}",
        }
    else:
        proxy_dict = {
            "http": proxy_url,
            "https": proxy_url,
        }
        
    try:
        start_time = time.time()
        # Ping Twitter or Google
        r = requests.get('https://twitter.com', proxies=proxy_dict, timeout=10)
        end_time = time.time()
        
        duration_ms = int((end_time - start_time) * 1000)
        
        if r.status_code == 200:
            proxy.status = 'Active'
            proxy.response_time = duration_ms
        else:
            proxy.status = 'Dead' # Or maybe banned
            
    except Exception as e:
        print(f"Proxy check failed: {e}")
        proxy.status = 'Dead'
        proxy.response_time = 0
        
    proxy.last_checked = datetime.datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'status': proxy.status, 'time': proxy.response_time})

@app.route('/check_all_proxies')
def check_all_proxies():
    # This should ideally be a threaded task
    # For now, we return a message to use individual checks to verify connectivity safely
    return jsonify({'success': True, 'message': 'Please use individual checks for now to ensure accuracy and avoid timeouts.'})

@app.route('/delete_dead_proxies', methods=['POST'])
def delete_dead_proxies():
    deleted = Proxy.query.filter_by(status='Dead').delete()
    db.session.commit()
    return jsonify({'success': True, 'count': deleted})

@app.route('/generate_ai_tweets', methods=['POST'])
def generate_ai_tweets_route():
    data = request.json
    topic = data.get('topic')
    tone = data.get('tone')
    lang = data.get('lang', 'ar')
    
    # Get settings for API Key
    settings = Settings.query.first()
    api_key = settings.groq_api_key if settings else None
    
    if not api_key:
        return jsonify({'success': False, 'message': 'API Key not configured in Settings'})
        
    from core.ai_client import AIGenerator
    ai = AIGenerator(api_key=api_key)
    
    tweets = ai.generate_tweets(topic, tone, lang)
    
    # Check if result looks like error
    if len(tweets) > 0 and "Error" in tweets[0]:
         return jsonify({'success': False, 'message': tweets[0]})
         
    return jsonify({'success': True, 'tweets': tweets})


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.svg', mimetype='image/svg+xml')


if __name__ == '__main__':
    # Create DB if not exists
    with app.app_context():
        db.create_all()

    # Ensure engine only starts in the main process (reloader fix)
    # We rely on WERKZEUG_RUN_MAIN to ensure we are in the reloader child process (where the server runs)
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("Starting Support Engine (Child Process)...")
        engine = SupportEngine(app)
        app.support_engine = engine # Attach to app for global access
        engine.start_background_thread()
        
        # Start Health Scheduler (Simple Background Thread)
        def run_health_scheduler(app_instance):
            with app_instance.app_context():
                print("Starting Health Scheduler...")
                while True:
                    try:
                        # Check accounts scheduled for auto-check or every X hours
                        # For simplicity, we check accounts not checked in 24h
                        now = datetime.datetime.utcnow()
                        cutoff = now - datetime.timedelta(hours=24)
                        
                        accounts_to_check = Account.query.filter(
                            (Account.last_health_check == None) | (Account.last_health_check < cutoff)
                        ).limit(5).all() # Limit batch size
                        
                        if accounts_to_check:
                            print(f"[HealthScheduler] Found {len(accounts_to_check)} accounts to check.")
                            # Call the parallel check function internal logic or engine logic
                            # We can re-use the check logic if abstracted, or just update metadata here to queue them
                            pass 
                    except Exception as e:
                        print(f"[HealthScheduler] Error: {e}")
                    
                    time.sleep(3600) # Check every hour

        scheduler_thread = threading.Thread(target=run_health_scheduler, args=(app,), daemon=True)
        scheduler_thread.start()
    
    app.run(debug=True, port=5000)
