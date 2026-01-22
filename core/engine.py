
from core.browser import TwitterBot
from models import SupportTask, ActionLog, Account, MonitoredAccount, Settings, Campaign, Proxy
from extensions import db
from core.utils import HumanBehavior
from core.ai_client import AIGenerator
import datetime
import threading
import time
import random
import json

class SupportEngine:
    def __init__(self, app):
        self.app = app
        self.is_running = False
        # Removed persistent temp_bot to prevent loop conflicts
        # self.temp_bot = TwitterBot(headless=True)

    def process_queue(self):
        """
        Main loop to process pending support tasks.
        This should be run in a separate thread.
        """
        self.is_running = True
        last_check_time = datetime.datetime.min # Initialize generic time
        
        while self.is_running:
            with self.app.app_context():
                try:
                    now = datetime.datetime.utcnow()
                    
                    # 1. Check Monitored Accounts (Periodic)
                    if (now - last_check_time).total_seconds() > 60:
                       print("Checking monitored accounts...")
                       self.check_monitored_accounts()
                       last_check_time = now
                    
                    # 1.5 Process Active Campaigns (Drip Feed)
                    self.process_active_campaigns()

                    # 2. Process Pending Support Tasks (Scheduled)
                    # Filter for Pending tasks where scheduled_time is NOW or in the PAST
                    pending_task = SupportTask.query.filter(
                        SupportTask.status == 'Pending',
                        SupportTask.scheduled_time <= now
                    ).first()
                    
                    if pending_task:
                        print(f"Processing Scheduled Task: {pending_task.id} - {pending_task.task_type}")
                        pending_task.status = 'In Progress'
                        db.session.commit()
                        
                        self.execute_task(pending_task)
                        
                        pending_task.status = 'Completed'
                        pending_task.completed_count = pending_task.target_count
                        db.session.commit()
                    else:
                        time.sleep(5) # Sleep only if no task was processed
                        
                except Exception as e:
                    print(f"Error in process_queue loop: {e}")
                    time.sleep(5)

    def get_system_proxy(self):
        """Fetches a high-quality proxy from the dedicated Proxy pool."""
        # Prioritize Active proxies with low latency
        proxies = Proxy.query.filter_by(status='Active').order_by(Proxy.response_time.asc()).limit(20).all()
        if proxies:
            return random.choice(proxies).proxy_string
        return None

    def check_monitored_accounts(self):
        try:
             # Only check active accounts
             monitored = MonitoredAccount.query.filter_by(is_active=True).all()
             if not monitored:
                 return

             # Use active accounts for scraping (load balance)
             scraper_accounts = Account.query.filter_by(status='Active').all()
             if not scraper_accounts:
                 print("No active account found for scraping monitoring tasks.")
                 return

             print(f"Starting parallel check for {len(monitored)} accounts...")

             from concurrent.futures import ThreadPoolExecutor
             
             # Max workers = 3 to be safe on local machine resources
             with ThreadPoolExecutor(max_workers=3) as executor:
                 futures = []
                 for account in monitored:
                     # Assign a random scraper account for this task
                     assigned_scraper = random.choice(scraper_accounts)
                     futures.append(executor.submit(self.process_single_account_check, account.id, assigned_scraper.id))
                 
                 # Wait for all to complete (optional, or just let them run)
                 for future in futures:
                     try:
                         future.result()
                     except Exception as exc:
                         print(f"Thread generated an exception: {exc}")

        except Exception as e:
             print(f"Error in monitoring loop: {e}")

    def rotate_proxy(self, account):
        """
        Rotates the proxy for a given account.
        Marks old proxy as Suspended (if recorded) and assigns a new Active one.
        """
        from extensions import add_system_log
        
        try:
            # 1. Mark current proxy as Suspended (if it matches a known proxy record)
            if account.proxy:
                old_proxy_record = Proxy.query.filter_by(proxy_string=account.proxy).first()
                if old_proxy_record:
                    old_proxy_record.status = 'Suspended'
                    old_proxy_record.last_checked = datetime.datetime.utcnow()
                    db.session.commit()
                    add_system_log(f"Suspended bad proxy for {account.username}", 'warning')

            # 2. Get new proxy
            new_proxy = self.get_system_proxy()
            if new_proxy:
                account.proxy = new_proxy
                db.session.commit()
                add_system_log(f"Rotated proxy for {account.username} -> New Proxy assigned.", 'success')
                print(f"Proxy Rotated for {account.username}: {new_proxy}")
                return True
            else:
                add_system_log(f"No active proxies available for {account.username}!", 'error')
                return False

        except Exception as e:
            print(f"Error rotating proxy: {e}")
            return False

    def process_single_account_check(self, monitored_account_id, scraper_account_id):
        """Worker function for parallel execution"""
        # Create a NEW app context for this thread
        with self.app.app_context():
            bot = None
            try:
                # Re-fetch objects within this thread's session
                account = MonitoredAccount.query.get(monitored_account_id)
                scraper_account = Account.query.get(scraper_account_id)
                
                if not account or not scraper_account:
                    return

                # Calculate interval check
                now = datetime.datetime.utcnow()
                if account.last_checked:
                    elapsed_minutes = (now - account.last_checked).total_seconds() / 60
                    if elapsed_minutes < account.check_interval:
                        return # Skip if too soon

                bot = TwitterBot(headless=True)
                
                # Proxy Setup
                proxy_to_use = scraper_account.proxy
                if not proxy_to_use:
                    # We need to access get_system_proxy via self, but self is thread-safe here for read
                    # However, get_system_proxy queries DB, so it needs context. We are in context.
                    proxy_to_use = self.get_system_proxy()
                
                bot.start_browser(proxy=proxy_to_use, user_agent=scraper_account.user_agent)
                
                if scraper_account.cookies:
                    bot.load_cookies(scraper_account.cookies)

                # Check/Update Profile Info (if missing)
                if not account.display_name or not account.profile_image_url:
                    # print(f"Fetching profile details for {account.username}...")
                    d_name, p_img = bot.get_profile_details(account.username)
                    if d_name:
                        account.display_name = d_name
                        account.profile_image_url = p_img
                        db.session.commit()

                from extensions import add_system_log
                add_system_log(f"Checking updates for {account.username}...", 'info')
                print(f"Checking updates for {account.username} (Threaded)...")
                
                # Fetch recent tweets with timestamps
                # (Returns list of {'url': '...', 'created_at': '...'})
                recent_tweets = bot.get_recent_original_tweets(account.username, limit=5)
                
                if not recent_tweets:
                    print(f"No recent tweets found for {account.username}")
                    account.last_checked = datetime.datetime.utcnow()
                    db.session.commit()
                    return

                # Sort by date descending (Newest first) just in case
                # ISO format sorts correctly as string usually, but let's trust the scraper order (top to bottom)
                # Usually top is newest.
                
                today_date = datetime.datetime.utcnow().date()
                new_tasks_count = 0
                newest_tweet_url = recent_tweets[0]['url']
                
                task_types = account.task_type.split(',') if account.task_type else ['like']

                for tweet in recent_tweets:
                    t_url = tweet['url']
                    t_time_str = tweet['created_at']
                    
                    # Parse Date
                    try:
                        # Handle '2023-10-27T10:00:00.000Z'
                        if t_time_str:
                            t_dt = datetime.datetime.strptime(t_time_str.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S.000%z")
                            t_date = t_dt.date()
                        else:
                            continue # No date, skip
                    except:
                        # Fallback for simple parsers
                         continue

                    # Condition 1: Must be from TODAY
                    if t_date != today_date:
                        continue # Skip old tweets
                        
                    # Condition 2: Must NOT have been processed already
                    existing_task = SupportTask.query.filter_by(target_url=t_url).first()
                    if existing_task:
                        continue # Already added
                    
                    # Add Task (Detected missed tweet from today)
                    add_system_log(f"Found new tweet for {account.username}: {t_url}", 'success')
                    print(f"Queueing missed tweet from {t_date}: {t_url}")
                    
                    actions = []
                    has_like = 'like' in task_types
                    has_retweet = 'retweet' in task_types
                    
                    if 'both' in task_types or (has_like and has_retweet):
                        actions.append('both')
                    else:
                        if has_like: actions.append('like')
                        if has_retweet: actions.append('retweet')
                    
                    if 'reply' in task_types: actions.append('reply')
                    
                    for action in set(actions):
                        new_task = SupportTask(
                            target_url=t_url,
                            task_type=action,
                            target_count=10, 
                            status='Pending'
                        )
                        db.session.add(new_task)
                        new_tasks_count += 1
                        
                        if action == 'both':
                             account.stats_likes += 1
                             account.stats_retweets += 1
                        elif action == 'like':
                             account.stats_likes += 1
                        elif action == 'retweet':
                             account.stats_retweets += 1
                
                # Update State
                if new_tasks_count > 0:
                     print(f"Queued {new_tasks_count} missed tasks for {account.username}.")
                
                # Always update the 'last_tweet_url' to the absolute newest one we saw
                # So next time we know where we stand (though date logic overrides this mainly)
                if newest_tweet_url != account.last_tweet_url:
                    account.last_tweet_url = newest_tweet_url
                
                account.last_checked = datetime.datetime.utcnow()
                db.session.commit()
                return
            
            except Exception as e:
                err_msg = str(e).lower()
                print(f"Error processing {monitored_account_id} in thread: {e}")
                
                # Smart Proxy Rotation Trigger
                if "timeout" in err_msg or "connection" in err_msg or "network" in err_msg or "target closed" in err_msg:
                    print(f"Connection error detected for scraper. Triggering Proxy Rotation...")
                    if self.rotate_proxy(scraper):
                         print(f"Proxy rotated for scraper due to error.")
            finally:
                if bot:
                    bot.close()
            
    def execute_task(self, task):
        # Get active accounts
        accounts = Account.query.filter_by(status='Active').limit(task.target_count).all()
        
        for account in accounts:
            print(f"Account {account.username} performing action...")
            
            # Check if this account already performed this action on this target
            existing_log = ActionLog.query.filter_by(
                account_id=account.id, 
                task_id=task.id, 
                action_type=task.task_type
            ).first()
            
            if existing_log:
                print(f"Account {account.username} already performed this action. Skipping.")
                continue

            bot = TwitterBot(headless=False) # Headless=False for demo viewing
            try:
                bot.start_browser(proxy=account.proxy, user_agent=account.user_agent)
                if account.cookies:
                    bot.load_cookies(account.cookies)
                
                # Perform Action
                success = False
                if task.task_type == 'like':
                    success = bot.like_tweet(task.target_url)
                # Unified Session Execution (Human-Like Sequence)
                # Initialize AI Generator if needed
                settings = Settings.query.first()
                ai_generator = None
                if settings and settings.ai_api_key:
                     from core.ai_client import AIGenerator
                     ai_generator = AIGenerator(
                         api_key=settings.ai_api_key,
                         provider=settings.ai_provider,
                         model=settings.ai_model,
                         system_prompt=settings.ai_system_prompt
                     )
                
                # Execute Sequence
                try:
                    actions_list = []
                    if task.task_type == 'both':
                        actions_list = ['like', 'retweet']
                    elif task.task_type == 'reply':
                        actions_list = ['reply']
                    else:
                        actions_list = [task.task_type]
                        
                    success = bot.perform_engagement_sequence(task.target_url, actions_list, ai_generator=ai_generator)
                except Exception as e:
                    print(f"Error executing task for {account.username}: {e}")
                    # Proxy Check
                    err_msg = str(e).lower()
                    if "timeout" in err_msg or "connection" in err_msg or "network" in err_msg or "target closed" in err_msg:
                         print(f"Connection error executing task for {account.username}. Rotating Proxy...")
                         self.rotate_proxy(account)
                    success = False
                # Legacy logic removed.
                
                if success:
                    log = ActionLog(
                        account_id=account.id,
                        task_id=task.id,
                        action_type=task.task_type,
                        target=task.target_url,
                        status='Success',
                        details=reply_content if task.task_type == 'reply' else None
                    )
                    db.session.add(log)
                    task.completed_count += 1
                    
                    # Update Account Stats
                    if task.task_type == 'like':
                        account.likes_count += 1
                    elif task.task_type == 'retweet':
                        account.retweets_count += 1
                    elif task.task_type == 'both':
                        account.likes_count += 1
                        account.retweets_count += 1

                    # Update Task Status
                    if task.completed_count >= task.target_count:
                        task.status = 'Completed'
                    else:
                        task.status = 'In Progress'
                        
                    db.session.commit()
                    print(f"Task {task.id}: {task.task_type} success on {task.target_url}")
                else:
                    print(f"Task {task.id}: Failed to {task.task_type}")

            except Exception as e:
                print(f"Error with account {account.username}: {e}")
                # Log error
                err_log = ActionLog(
                    account_id=account.id,
                    task_id=task.id if task else None,
                    action_type='error',
                    target=str(e)[:250] if e else "Unknown Error",
                    status='Failed'
                )
                db.session.add(err_log)
                db.session.commit()
            
            finally:
                if bot:
                     bot.close()
                # Random delay between accounts processing the same task
                # Increased for safety as per user request
                HumanBehavior.sleep_random(15, 30)

    def process_active_campaigns(self):
        try:
            # 0. Check for Scheduled Campaigns to Activate
            scheduled_campaigns = Campaign.query.filter_by(status='Scheduled').all()
            for sc in scheduled_campaigns:
                if sc.scheduled_time and sc.scheduled_time <= datetime.datetime.utcnow():
                    print(f"Activating scheduled campaign: {sc.name}")
                    sc.status = 'Active'
                    db.session.commit()

            active_campaigns = Campaign.query.filter_by(status='Active').all()
            if not active_campaigns:
                return

            now = datetime.datetime.utcnow()
            
            # Use an active account for scraping/bot actions
            scraper_account = Account.query.filter_by(status='Active').first()
            if not scraper_account:
                return

            for campaign in active_campaigns:
                # 1. Check if campaign is completed
                if campaign.completed_quantity >= campaign.target_quantity:
                    campaign.status = 'Completed'
                    db.session.commit()
                    continue
                
                # 2. Check Speed/Delay
                # Speed 1=Fast, 3=Normal, 5=Slow
                # Randomized delays for human-like behavior
                delay_map = {
                    1: (8, 15),     # Fast: 8-15s
                    2: (20, 45),    # Medium-Fast: 20-45s
                    3: (50, 90),    # Normal: 50-90s
                    4: (100, 180),  # Slow: 100-180s
                    5: (250, 400)   # Safe: 250-400s
                }
                
                min_delay, max_delay = delay_map.get(campaign.speed, (50, 90))
                # We can't know the exact random value used last time unless we store "next_run"
                # For simplicity, we just ensure at least the MIN delay has passed
                # To be even smarter, we could store 'next_run_time' in DB, but let's just use min_delay for logic check
                # and actually sleep/wait if needed? No, we just skip.
                
                # Correction: To truly randomize, we should have stored a 'next_run' timestamp. 
                # Since we only have 'last_run', we will check against a random threshold calculated NOW.
                # This works statistically.
                current_random_threshold = random.randint(min_delay, max_delay)
                
                if campaign.last_run:
                    elapsed = (now - campaign.last_run).total_seconds()
                    if elapsed < current_random_threshold:
                        continue

                # 2.5 Resolve Target (Tweet vs Profile)
                raw_input = campaign.target_input.strip()
                target_url = raw_input
                target_is_profile = False
                username = None
                
                # Enhanced Logic to detect Profile vs Tweet
                if raw_input.startswith('@'):
                    target_is_profile = True
                    username = raw_input.replace('@', '')
                elif "twitter.com" in raw_input or "x.com" in raw_input:
                    if "/status/" not in raw_input:
                        target_is_profile = True
                        # Clean args ?ref_src etc
                        clean_url = raw_input.split('?')[0]
                        username = clean_url.split('/')[-1]
                elif "/" not in raw_input and " " not in raw_input:
                    # Plain username "Hamza_Ameer8"
                    target_is_profile = True
                    username = raw_input

                if target_is_profile and username:
                    print(f"Campaign {campaign.name}: Starting Full-Batch Execution for {username}")
                    
                    # Calculate total remaining actions
                    remaining_quantity = campaign.target_quantity - campaign.completed_quantity
                    if remaining_quantity <= 0:
                        campaign.status = 'Completed'
                        db.session.commit()
                        continue

                    # Get all active accounts
                    all_accounts = Account.query.filter_by(status='Active').all()
                    random.shuffle(all_accounts)
                    
                    # Iterate through accounts until we fill the quota
                    for selected_account in all_accounts:
                        if remaining_quantity <= 0:
                            break
                            
                        print(f"Campaign {campaign.name}: Selecting {selected_account.username} to perform up to {remaining_quantity} actions.")
                        
                        bot = TwitterBot(headless=False)
                        try:
                            # Proxy Selection Logic
                            use_proxy = selected_account.proxy
                            if not use_proxy:
                                use_proxy = self.get_system_proxy()
                                if use_proxy:
                                    print(f" [Engine] Using System Proxy: {use_proxy.split('@')[-1] if '@' in use_proxy else use_proxy}")

                            bot.start_browser(proxy=use_proxy, user_agent=selected_account.user_agent)
                            if selected_account.cookies:
                                bot.load_cookies(selected_account.cookies)
                            
                            camp_actions = json.loads(campaign.actions) if campaign.actions else ['like']
                            
                            # Execute Batch (Generator Mode)
                            generator = bot.execute_profile_engagement(username, actions=camp_actions, limit=remaining_quantity)
                            
                            actions_in_this_session = 0
                            
                            for tweet_url, action_done in generator:
                                 actions_in_this_session += 1
                                 
                                 log = ActionLog(
                                    account_id=selected_account.id,
                                    action_type=action_done,
                                    target=tweet_url,
                                    status='Success',
                                    details=f"Campaign: {campaign.name} | Batch Mode"
                                 )
                                 db.session.add(log)

                                 # Update Account Stats
                                 if action_done == 'like':
                                     selected_account.likes_count += 1
                                 elif action_done == 'retweet':
                                     selected_account.retweets_count += 1
                                 
                                 # Update Campaign Progress Immediately
                                 campaign.completed_quantity += 1
                                 remaining_quantity -= 1
                                 campaign.last_run = now
                                 
                                 if campaign.completed_quantity >= campaign.target_quantity:
                                     campaign.status = 'Completed'
                                 
                                 db.session.commit() # Commit after each action
                                 print(f"Campaign Progress Updated: {campaign.completed_quantity}/{campaign.target_quantity}")
                                 
                                 if remaining_quantity <= 0:
                                     break

                            print(f"Campaign {campaign.name}: {selected_account.username} performed {actions_in_this_session} actions.")
                            
                        except Exception as e:
                            print(f"Batch execution error with {selected_account.username}: {e}")
                        finally:
                            bot.close()
                            
                        # Human pause between switching accounts
                        if remaining_quantity > 0:
                             print("Switching account in 10-20 seconds...")
                             time.sleep(random.randint(10, 20))

                    continue

                # --- END BATCH LOGIC ---
                # Fallback to Atomic Logic for Single Tweet URLs (Old Code)
                
                # Ensure Target URL is valid
                if not target_url.startswith('http'):
                    # If it somehow got here and isn't a http url (e.g. failed profile detection or logic error)
                    # Try to fix it if it looks like a tweet ID? No, assume it's a URL missing protocol
                    if "twitter.com" in target_url or "x.com" in target_url:
                         target_url = f"https://{target_url}"
                    else:
                         # Fallback/Error prevetion
                         print(f"Campaign {campaign.name}: Invalid Target URL '{target_url}'. Skipping.")
                         continue

                # 3. Select Action
                actions = json.loads(campaign.actions) if campaign.actions else ['like']
                action_to_do = random.choice(actions)
                
                # 4. Find valid account (that hasn't done this action on this target)
                all_accounts = Account.query.filter_by(status='Active').all()
                random.shuffle(all_accounts) 
                
                selected_account = None
                for acc in all_accounts:
                    exists = ActionLog.query.filter_by(
                        account_id=acc.id,
                        action_type=action_to_do,
                        target=target_url 
                    ).first()
                    
                    if not exists:
                        selected_account = acc
                        break
                
                if not selected_account:
                    print(f"Campaign {campaign.name}: No available accounts for {action_to_do} on {target_url}")
                    continue

                # 5. Execute Action
                print(f"Campaign {campaign.name}: Executing {action_to_do} with {selected_account.username}")
                bot = None
                success = False
                try:
                    bot = TwitterBot(headless=False)
                    bot.start_browser(proxy=selected_account.proxy, user_agent=selected_account.user_agent)
                    if selected_account.cookies:
                         bot.load_cookies(selected_account.cookies)
                    
                    # Human Behavior stuff
                    if random.random() > 0.7:
                        bot.page.goto("https://twitter.com/home")
                        HumanBehavior.sleep_random(2, 5)
                    
                    bot.page.goto(target_url)
                    HumanBehavior.sleep_random(3, 6)
                    bot.simulate_reading()
                    
                    msg = None
                    if action_to_do == 'like':
                         # Since we navigated to target_url above, we are good
                        success = bot.like_tweet(target_url) 
                    elif action_to_do == 'retweet':
                        success = bot.retweet(target_url)
                    elif action_to_do == 'reply':
                         settings = Settings.query.first()
                         if settings and settings.ai_api_key:
                              tweet_text = bot.get_tweet_text(target_url)
                              if tweet_text:
                                   ai = AIGenerator(settings.ai_api_key, settings.ai_provider, settings.ai_model, settings.ai_system_prompt)
                                   reply_content = ai.generate_reply(tweet_text)
                                   if "Error" not in reply_content:
                                        success = bot.reply_to_tweet(target_url, reply_content)
                                        msg = reply_content

                    if success:
                        log = ActionLog(
                            account_id=selected_account.id,
                            action_type=action_to_do,
                            target=target_url,
                            status='Success',
                            details=f"Campaign: {campaign.name} | {msg if msg else ''}"
                        )
                        db.session.add(log) # Log the specific action on specific tweet

                        # Update Account Stats
                        if action_to_do == 'like':
                            selected_account.likes_count += 1
                        elif action_to_do == 'retweet':
                            selected_account.retweets_count += 1
                        
                        # IMPORTANT: If it's a profile campaign, we might want to log that we acted on the profile too?
                        # But for now, ActionLog 'target' is specific. 
                        # We just increment the campaign counter.
                        
                        campaign.completed_quantity += 1
                        campaign.last_run = now
                        
                        if campaign.completed_quantity >= campaign.target_quantity:
                            campaign.status = 'Completed'
                            
                        db.session.commit()
                        print(f"Campaign action success.")
                    else:
                        print(f"Campaign action failed.")

                except Exception as e:
                    print(f"Campaign execution error: {e}")
                finally:
                    if bot:
                        bot.close()

        except Exception as e:
            print(f"Error in process_active_campaigns: {e}")

    def start_background_thread(self):
        thread = threading.Thread(target=self.process_queue)
        thread.daemon = True
        thread.start()
