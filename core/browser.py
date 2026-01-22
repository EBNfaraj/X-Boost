from playwright.sync_api import sync_playwright
import time
import random
from core.utils import HumanBehavior
import json

class TwitterBot:
    def __init__(self, headless=False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    def start_browser(self, proxy=None, user_agent=None):
        self.playwright = sync_playwright().start()
        
        launch_args = [
             "--disable-blink-features=AutomationControlled"
        ]
        
        browser_config = {
            "headless": self.headless,
            "args": launch_args
        }
        
        if proxy:
            browser_config["proxy"] = {"server": proxy}

        self.browser = self.playwright.chromium.launch(**browser_config)
        
        context_config = {
            "viewport": {"width": 1280, "height": 720},
            "user_agent": user_agent if user_agent else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        
        self.context = self.browser.new_context(**context_config)
        self.page = self.context.new_page()

    def load_cookies(self, cookies):
        if cookies:
            cookie_list = json.loads(cookies) if isinstance(cookies, str) else cookies
            
            # Sanitize cookies
            for cookie in cookie_list:
                if 'sameSite' in cookie:
                    ss = cookie['sameSite']
                    if ss is None:
                        cookie['sameSite'] = 'None'
                        continue
                        
                    if ss in ['no_restriction', 'unspecified']:
                        cookie['sameSite'] = 'None'
                    elif isinstance(ss, str):
                        if ss.lower() == 'lax':
                            cookie['sameSite'] = 'Lax'
                        elif ss.lower() == 'strict':
                            cookie['sameSite'] = 'Strict'
                        elif ss.lower() == 'none':
                            cookie['sameSite'] = 'None'
                        elif ss not in ['Strict', 'Lax', 'None']:
                            cookie.pop('sameSite', None)
                    else:
                         # If it's not None and not a string/valid, remove it
                         cookie.pop('sameSite', None)
            
            try:
                self.context.add_cookies(cookie_list)
            except Exception as e:
                print(f"Error loading cookies: {e}")

    def login(self, username, password):
        """
        Basic login flow. 
        Note: Ideally, we use cookies to avoid this. 
        But this is a fallback.
        """
        self.page.goto("https://twitter.com/i/flow/login")
        HumanBehavior.sleep_random(3, 5)
        
        # Enter Username
        self.page.fill("input[autocomplete='username']", username)
        self.page.click("text=Next")
        HumanBehavior.sleep_random(2, 4)
        
        # Enter Password
        if self.page.is_visible("input[name='password']"):
             self.page.fill("input[name='password']", password)
             self.page.click("text=Log in")
        # Handle "Phone/Email verification" case if needed
        
        HumanBehavior.sleep_random(5, 7)
    
    def simulate_reading(self):
        """
        Simulates a user reading a tweet by scrolling down and up 
        and pausing for a random duration, with mouse jitter.
        """
        # Mouse Jitter (Move mouse randomly on page)
        try:
             # Get current viewport size to stay within bounds
             viewport = self.page.viewport_size
             if viewport:
                 start_x = random.randint(100, viewport['width'] - 100)
                 start_y = random.randint(100, viewport['height'] - 100)
                 self.page.mouse.move(start_x, start_y)
                 
                 # Move to another random spot
                 end_x = random.randint(100, viewport['width'] - 100)
                 end_y = random.randint(100, viewport['height'] - 100)
                 
                 # Use utils to calculate path
                 path = HumanBehavior.calculate_mouse_movement(start_x, start_y, end_x, end_y)
                 for x, y in path:
                     self.page.mouse.move(x, y)
                     # Ultra fast sleep for movement smoothness
                     time.sleep(random.uniform(0.001, 0.005))
        except Exception as e:
            print(f"Mouse sim error: {e}")

        # Scroll down a bit (reading replies/thread)
        scroll_amount = HumanBehavior.get_random_scroll_amount()
        self.page.mouse.wheel(0, scroll_amount)
        HumanBehavior.sleep_random(2, 5) # Time to read
        
        # Maybe scroll a bit more
        if random.random() > 0.5:
             self.page.mouse.wheel(0, scroll_amount / 2)
             HumanBehavior.sleep_random(1, 3)
        
        # Scroll back up to the tweet
        self.page.mouse.wheel(0, -scroll_amount * 1.5)
        HumanBehavior.sleep_random(1, 2)

    def like_tweet(self, tweet_url):
        self.page.goto(tweet_url)
        HumanBehavior.sleep_random(3, 5) # Initial load wait
        
        # Simulate Reading Behavior
        self.simulate_reading()
        
        try:
            # Target the first article (tweet) to avoid liking replies
            # Use .first to ensure we only get one element even if selector matches multiple (strictly 1st)
            like_button = self.page.locator("article").first.locator("button[data-testid='like']").first
            
            # Wait for element to be visible/enabled
            if like_button.count() > 0:
                like_button.click()
                print(f"Liked {tweet_url}")
                return True
            else:
                # Check if already liked (unlike button)
                unlike = self.page.locator("article").first.locator("button[data-testid='unlike']").first
                if unlike.count() > 0:
                    print("Already liked")
                    return True # Treat as success
                    
                print("Like button not found")
                return False
        except Exception as e:
            print(f"Error liking tweet: {e}")
            return False

    def retweet(self, tweet_url):
        self.page.goto(tweet_url)
        HumanBehavior.sleep_random(3, 5)
        
        # Simulate Reading Behavior
        self.simulate_reading()
        
        try:
            # Target first article's retweet button
            retweet_button = self.page.locator("article").first.locator("button[data-testid='retweet']").first
            
            if retweet_button.count() > 0:
                retweet_button.click()
                HumanBehavior.sleep_random(1, 2)
                
                # Confirm Retweet (in the dropdown/modal)
                confirm_button = self.page.locator("div[data-testid='retweetConfirm']").first
                if confirm_button.count() > 0:
                     confirm_button.click()
                     print(f"Retweeted {tweet_url}")
                     return True
            else:
                 # Check if already retweeted
                 unretweet = self.page.locator("article").first.locator("button[data-testid='unretweet']").first
                 if unretweet.count() > 0:
                     print("Already retweeted")
                     return True

            return False
        except Exception as e:
            print(f"Error retweeting: {e}")
            return False

    def get_profile_details(self, username):
        """
        Scrapes the profile image and display name.
        """
        profile_url = f"https://twitter.com/{username}"
        try:
            self.page.goto(profile_url, timeout=30000)
            self.page.wait_for_selector("article", timeout=30000)
        except Exception as e:
            print(f"Error loading profile for details: {e}")
            return None, None
            
        HumanBehavior.sleep_random(2, 4)
        
        try:
            # Get Display Name
            # Usually in the header: h2 span -> text
            # Or strict selector: div[data-testid='UserName'] span span
            name_element = self.page.locator("div[data-testid='UserName'] span").first
            display_name = name_element.inner_text() if name_element.count() > 0 else username
            
            # Get Profile Image
            # Selector: img[alt='Opens profile photo'] or similar
            # More specific: a[href='/<username>/photo'] img
            # Or generically the first image in the header area
            # Let's try UserAvatar-Container
            avatar_img = self.page.locator(f"a[href='/{username}/photo'] img").first
            
            # Fallback if the photo link structure is different (sometimes it is)
            # Fallback for header image
            if avatar_img.count() == 0:
                 avatar_img = self.page.locator("div[data-testid='primaryColumn'] img[src*='profile_images']").first

            # Try getting src
            profile_image_url = None
            if avatar_img.count() > 0:
                 profile_image_url = avatar_img.get_attribute("src")
            
            # Fallback: Scrape from metadata if on profile page
            if not display_name or not profile_image_url:
                 try:
                     meta_title = self.page.title()
                     # Title is usually "Name (@user) / Twitter"
                     if "(" in meta_title:
                         display_name = meta_title.split("(")[0].strip()
                 except: pass

            return display_name, profile_image_url
            
        except Exception as e:
            print(f"Error extracting profile details: {e}")
            return None, None

    def get_latest_tweet(self, username):
        """
        Navigates to user profile and returns the URL of the first tweet found.
        """
        profile_url = f"https://twitter.com/{username}"
        profile_url = f"https://twitter.com/{username}"
        
        # Retry logic for navigation
        success = False
        for attempt in range(3):
            try:
                print(f"Navigating to {profile_url} (Attempt {attempt+1}/3)...")
                # timeout=60000 is generous, but we catch it now. 
                # waitUntil='domcontentloaded' is faster than 'load'
                self.page.goto(profile_url, timeout=45000, wait_until='domcontentloaded')
                success = True
                break
            except Exception as e:
                print(f"Navigation failed (Attempt {attempt+1}): {e}")
                HumanBehavior.sleep_random(2, 5)
        
        if not success:
            return None

        try:
            # Wait specifically for the timeline to appear
            # Wait specifically for the timeline to appear
            try:
                self.page.wait_for_selector("article", timeout=30000)
            except:
                # Double check if profile loaded but no tweets (e.g. protected/empty)
                if self.page.locator("div[data-testid='primaryColumn']").count() > 0:
                     print(f"Profile loaded but no tweets found for {username}")
                     return None
                raise # Re-raise if page didn't load at all
        except Exception as e:
            print(f"Timeout or error loading profile: {e}")
            return None
            
        HumanBehavior.sleep_random(2, 4)
        
        try:
            # Look for articles (tweets)
            articles = self.page.locator("article")
            count = articles.count()
            
            if count > 0:
                # Iterate through the first 3 tweets to find the latest non-pinned one
                # or just the first one if no pin is detected.
                for i in range(min(3, count)):
                    tweet = articles.nth(i)
                    
                    # Check for "Pinned Tweet" indicator
                    # It usually appears in data-testid='socialContext'
                    social_context = tweet.locator("div[data-testid='socialContext']")
                    is_pinned = False
                    if social_context.count() > 0:
                        text = social_context.inner_text().lower()
                        # Check for English or Arabic "Pinned"
                        if "pinned" in text or "مثبتة" in text or "épinglé" in text:
                            print(f"Skipping Pinned Tweet at index {i}")
                            is_pinned = True
                    
                    if is_pinned:
                        continue

                    # Strategy 1: Look for time element
                    time_elements = tweet.locator("time")
                    if time_elements.count() > 0:
                        target_time = time_elements.first 
                        tweet_link_element = target_time.locator("xpath=..") 
                        href = tweet_link_element.get_attribute("href")
                        if href:
                            full_url = f"https://twitter.com{href}"
                            return full_url

                    # Strategy 2: Look for any link containing '/status/' inside the article
                    # This is a fallback
                    all_links = tweet.locator("a").all()
                    for link in all_links:
                        href = link.get_attribute("href")
                        if href and "/status/" in href and "/photo/" not in href and "/video/" not in href:
                            full_url = f"https://twitter.com{href}"
                            print(f"Latest tweet found (Strategy 2): {full_url}")
                            return full_url
                            
            print(f"No valid tweet URL found for {username}")
            return None        
        except Exception as e:
            print(f"Error extracting tweet: {e}")
            return None



    def execute_profile_engagement(self, username, actions=['like'], limit=3):
        """
        Navigates to profile and engages with multiple tweets in a single session.
        Performs ALL requested actions on each tweet sequentially.
        Returns the number of successful interactions (total actions count).
        """
        profile_url = f"https://twitter.com/{username}"
        total_actions_performed = 0
        
        try:
            print(f"Starting session engagement for {username} (Target limit: {limit})...")
            self.page.goto(profile_url, timeout=60000)
            self.page.wait_for_selector("article", timeout=30000)
            HumanBehavior.sleep_random(3, 5)
            
            # Initial scroll/read
            self.simulate_reading()
            
            processed_results = []
            processed_ids = set() # Track processed tweets to avoid duplicates
            scroll_attempts = 0
            max_scrolls = 100 # Increased significantly to ensure we find content
            
            while total_actions_performed < limit and scroll_attempts < max_scrolls:
                # Find articles currently in DOM
                articles = self.page.locator("article").all()
                print(f"Scanning {len(articles)} tweets in view (scrolled {scroll_attempts} times)...")
                
                new_tweets_found_in_view = 0
                
                for article in articles:
                    if total_actions_performed >= limit:
                        break
                        
                    # Extract ID/Key
                    tweet_url = "unknown"
                    time_el = article.locator("time").first
                    if time_el.count() > 0:
                        parent = time_el.locator("xpath=..")
                        href = parent.get_attribute("href")
                        if href: tweet_url = f"https://twitter.com{href}"
                    
                    if tweet_url in processed_ids:
                        continue
                        
                    processed_ids.add(tweet_url)
                    new_tweets_found_in_view += 1
                        
                    # Filter Retweets (Fast Skip)
                    social_context = article.locator("span[data-testid='socialContext']").first
                    if social_context.count() > 0:
                         text = social_context.inner_text().lower()
                         if "reposted" in text or "retweeted" in text:
                             continue 
    
                    # Filter Non-User Tweets (Fast Skip)
                    user_name_div = article.locator("div[data-testid='User-Name']").first
                    if user_name_div.count() > 0:
                        text_content = user_name_div.inner_text().lower()
                        if f"@{username.lower()}" not in text_content:
                            continue
    
                # Scroll element into view
                try:
                    article.scroll_into_view_if_needed(timeout=5000)
                except:
                    # If scrolling fails, we might still be able to click or just skip
                    print("Scroll failed, attempting interaction anyway...")

                print(f"Engaging with Tweet: {tweet_url}")

                # Perform Actions Sequentially
                action_done_on_this_tweet = False
                
                # 1. LIKE
                if 'like' in actions and total_actions_performed < limit:
                    try:
                        like_btn = article.locator("button[data-testid='like']").first
                        if like_btn.count() > 0:
                            # Hover and Click
                            like_btn.hover()
                            HumanBehavior.sleep_random(0.2, 0.5)
                            like_btn.click(timeout=5000) # Short timeout
                            print("-> Liked")
                            yield (tweet_url, 'like') # Yield immediately
                            total_actions_performed += 1
                            action_done_on_this_tweet = True
                            HumanBehavior.sleep_random(2, 4) 
                        else:
                            # Check if already liked
                            unlike_btn = article.locator("button[data-testid='unlike']").first
                            if unlike_btn.count() > 0:
                                    print("-> Already Liked (Skipping)")
                                    HumanBehavior.sleep_random(0.1, 0.3)
                            else:
                                    print("-> Like button not found")
                    except Exception as e:
                        print(f"-> Like failed: {e}")

                # 2. RETWEET
                if 'retweet' in actions and total_actions_performed < limit:
                    try:
                        rt_btn = article.locator("button[data-testid='retweet']").first
                        if rt_btn.count() > 0:
                            rt_btn.click(timeout=5000)
                            HumanBehavior.sleep_random(1, 2)
                            confirm = self.page.locator("div[data-testid='retweetConfirm']").first
                            if confirm.count() > 0:
                                confirm.click(timeout=5000)
                                print("-> Retweeted")
                                yield (tweet_url, 'retweet') # Yield immediately
                                total_actions_performed += 1
                                action_done_on_this_tweet = True
                                HumanBehavior.sleep_random(2, 4)
                        else:
                                # Check unretweet
                                unrt_btn = article.locator("button[data-testid='unretweet']").first
                                if unrt_btn.count() > 0:
                                    print("-> Already Retweeted")
                                    HumanBehavior.sleep_random(0.1, 0.3)
                    except Exception as e:
                        print(f"-> Retweet failed: {e}")

                if action_done_on_this_tweet:
                        print("Done actions on this tweet. Pausing...")
                        HumanBehavior.sleep_random(2, 5)
                    
                    # If we just skipped it (already acted), we move immediately to next
                
                # End of current view processing
                if total_actions_performed >= limit:
                    break
                
                # Scroll Logic
                print("Scrolling for more tweets...")
                self.page.mouse.wheel(0, 1000)
                HumanBehavior.sleep_random(2, 4)
                scroll_attempts += 1

                
                # Check if we are stuck (feed end or no new items)
                # For now just max_scrolls limits us.

            return processed_results

        except Exception as e:
            print(f"Error in session engagement: {e}")
            return []

    def get_recent_original_tweets(self, username, limit=5):
        """
        Fetches the last N tweets from a user's profile, skipping retweets and replies.
        RETURNS: List of dicts -> [{'url': url, 'created_at': iso_string}, ...]
        """
        tweets_data = []
        try:
            profile_url = f"https://twitter.com/{username}"
            if self.page.url != profile_url:
                self.page.goto(profile_url)
                # Wait for timeline
                try:
                    self.page.wait_for_selector("article", timeout=15000)
                except:
                    print(f"Could not load timeline for {username}")
                    return []

            # Scroll to load few tweets
            self.page.mouse.wheel(0, 500)
            HumanBehavior.sleep_random(2, 3)

            # Get Articles
            articles = self.page.locator("article").all()
            print(f"Found {len(articles)} articles. Filtering...")

            for article in articles:
                if len(tweets_data) >= limit:
                    break
                    
                # Check for "Retweeted" or "Pinned" label (SocialContext)
                social_context = article.locator("span[data-testid='socialContext']").first
                if social_context.count() > 0:
                     text = social_context.inner_text().lower()
                     if "reposted" in text or "retweeted" in text:
                         continue # Skip Retweets
                     if "pinned" in text or "مثبتة" in text or "épinglé" in text:
                         continue # Skip Pinned Tweets
                
                # Extract Time & URL
                time_element = article.locator("time").first
                if time_element.count() > 0:
                    timestamp = time_element.get_attribute("datetime") # e.g., 2023-10-27T10:00:00.000Z
                    
                    tweet_link_element = time_element.locator("xpath=..")
                    href = tweet_link_element.get_attribute("href")
                    
                    if href:
                        full_url = f"https://twitter.com{href}"
                        tweets_data.append({'url': full_url, 'created_at': timestamp})
                        print(f"Found candidate: {full_url} ({timestamp})")
                
            return tweets_data

        except Exception as e:
            print(f"Error fetching recent tweets: {e}")
            return []

    def get_tweet_text(self, tweet_url):
        """
        Extracts the text content of the target tweet to feed into AI.
        """
        try:
            self.page.goto(tweet_url)
            self.page.wait_for_selector("article", timeout=15000)
            
            # Target the first article (the main tweet)
            article = self.page.locator("article").first
            
            # Text is usually in div[data-testid='tweetText']
            text_el = article.locator("div[data-testid='tweetText']").first
            if text_el.count() > 0:
                return text_el.inner_text()
            return ""
        except Exception as e:
            print(f"Error getting tweet text: {e}")
            return ""

    def reply_to_tweet(self, tweet_url, reply_text):
        """
        Replies to a tweet with the given text.
        """
        try:
            print(f"Replying to {tweet_url}...")
            # Navigate only if not already there (optimization for sequences)
            if self.page.url != tweet_url:
                self.page.goto(tweet_url)
                HumanBehavior.sleep_random(3, 5)
            
            # 1. Click Reply Icon (Button)
            # data-testid="reply"
            reply_icon = self.page.locator("article").first.locator("button[data-testid='reply']").first
            reply_icon.click()
            
            HumanBehavior.sleep_random(1, 2)
            
            # 2. Type Text
            # Contenteditable div usually
            editor = self.page.locator("div[class*='public-DraftEditor-content']").first
            if editor.count() == 0:
                 # Fallback if modal structure is different
                 editor = self.page.locator("div[data-testid='tweetTextarea_0']").first
            
            if editor.count() > 0:
                editor.click()
                editor.fill(reply_text)
                HumanBehavior.sleep_random(1, 3)
                
                # 3. Click Reply Button (Send)
                # data-testid="tweetButton"
                send_btn = self.page.locator("button[data-testid='tweetButton']").first
                send_btn.click()
                print("Reply sent successfully.")
                return True
            else:
                print("Could not find reply editor.")
                return False
                
        except Exception as e:
            print(f"Error replying to tweet: {e}")
            return False

    def perform_engagement_sequence(self, tweet_url, actions=['like'], ai_generator=None):
        """
        Performs a sequence of actions on a single tweet in one visit.
        This provides a much more human-like signature.
        """
        try:
            print(f"Starting engagement sequence on {tweet_url}: {actions}")
            self.page.goto(tweet_url)
            HumanBehavior.sleep_random(3, 6) # Initial load wait
            
            # Simulate Reading Behavior
            self.simulate_reading()
            
            # Locate the main article once
            try:
                article = self.page.locator("article").first
                article.wait_for(timeout=10000)
            except:
                print("Could not find article to engage with.")
                return False
            
            results = {}
            
            for action in actions:
                # 1. LIKE
                if action == 'like':
                    try:
                        like_btn = article.locator("button[data-testid='like']").first
                        if like_btn.count() > 0:
                            like_btn.hover()
                            HumanBehavior.sleep_random(0.5, 1.5)
                            like_btn.click()
                            print("-> Unified: Liked")
                            results['like'] = True
                        else:
                            # Check if already liked
                             if article.locator("button[data-testid='unlike']").count() > 0:
                                 print("-> Unified: Already Liked")
                                 results['like'] = True
                             else:
                                 results['like'] = False
                    except Exception as e:
                        print(f"Error liking in sequence: {e}")
                        results['like'] = False
                        
                    HumanBehavior.sleep_random(2, 5) # Pause between actions
                    
                # 2. RETWEET
                elif action == 'retweet':
                    try:
                        rt_btn = article.locator("button[data-testid='retweet']").first
                        if rt_btn.count() > 0:
                            rt_btn.hover()
                            HumanBehavior.sleep_random(0.5, 1.0)
                            rt_btn.click()
                            HumanBehavior.sleep_random(1, 2)
                            
                            confirm = self.page.locator("div[data-testid='retweetConfirm']").first
                            if confirm.count() > 0:
                                confirm.click()
                                print("-> Unified: Retweeted")
                                results['retweet'] = True
                        else:
                             if article.locator("button[data-testid='unretweet']").count() > 0:
                                 print("-> Unified: Already Retweeted")
                                 results['retweet'] = True
                             else:
                                 results['retweet'] = False
                    except Exception as e:
                        print(f"Error retweeting in sequence: {e}")
                        results['retweet'] = False
                        
                    HumanBehavior.sleep_random(2, 4)
                
                # 3. REPLY (AI POWERED)
                elif action == 'reply' and ai_generator:
                    try:
                        # Get Tweet Text context
                        tweet_text_element = article.locator("div[data-testid='tweetText']").first
                        if tweet_text_element.count() > 0:
                             tweet_text = tweet_text_element.inner_text()
                             print(f"Generating AI reply for: {tweet_text[:30]}...")
                             
                             generated_reply = ai_generator.generate_reply(tweet_text)
                             
                             if "Error" not in generated_reply:
                                 print(f"AI Replying: {generated_reply}")
                                 
                                 # Click Reply
                                 reply_icon = article.locator("button[data-testid='reply']").first
                                 reply_icon.click()
                                 HumanBehavior.sleep_random(1, 2)
                                 
                                 # Type & Send
                                 editor = self.page.locator("div[class*='public-DraftEditor-content']").first
                                 if editor.count() == 0:
                                      editor = self.page.locator("div[data-testid='tweetTextarea_0']").first
                                 
                                 if editor.count() > 0:
                                     editor.click()
                                     editor.fill(generated_reply)
                                     HumanBehavior.sleep_random(2, 4)
                                     
                                     send_btn = self.page.locator("button[data-testid='tweetButton']").first
                                     send_btn.click()
                                     print("-> Unified: AI Reply Sent")
                                     results['reply'] = True
                                 else:
                                     print("Could not find editor for AI reply")
                                     results['reply'] = False
                             else:
                                 print(f"Skipping reply due to generation error: {generated_reply}")
                                 results['reply'] = False
                        else:
                             print("Could not extract text for AI reply")
                             results['reply'] = False
                    except Exception as e:
                        print(f"Error replying in sequence: {e}")
                        results['reply'] = False
            
            # Return true if AT LEAST ONE of the requested actions succeeded
            return any(results.values())
            
        except Exception as e:
            print(f"Error in engagement sequence: {e}")
            return False

    def check_account_status(self, username, cookies):
        """
        Checks the health of the account using its cookies.
        Returns: 'Healthy', 'Suspended', 'Locked', or 'Invalid Cookies'
        """
        try:
            # 1. Load Cookies
            self.load_cookies(cookies)
            
            # 2. Go to Home
            self.page.goto("https://twitter.com/home", timeout=30000)
            HumanBehavior.sleep_random(3, 5)
            
            # 3. Check URL - if redirected to login, cookies are dead
            current_url = self.page.url
            if "login" in current_url or "flow/login" in current_url:
                print(f"Account {username}: Redirected to login. Cookies Invalid.")
                return "Invalid Cookies"
            
            # 4. Check for Suspension / Locked Banners
            # Look for specific text on the page
            content = self.page.content().lower()
            
            if "suspended" in content or "account suspended" in content:
                # Double check element existence to be sure
                if self.page.locator("text='Account suspended'").count() > 0:
                     print(f"Account {username}: Suspended.")
                     return "Suspended"
            
            if "locked" in content or "verify your identity" in content or "start" in content:
                 # Often locked accounts show a "Start" button for a challenge
                 if self.page.locator("text='Start'").count() > 0 or self.page.locator("text='Verify'").count() > 0:
                     print(f"Account {username}: Locked/Checkpoint.")
                     return "Locked"

            # 5. Check if we are actually logged in (Avatar or Home nav)
            # 5. Check if we are actually logged in (Avatar or Home nav)
            # Expanded selectors for mobile/desktop
            if (self.page.locator("a[aria-label='Home']").count() > 0 or 
                self.page.locator("div[data-testid='SideNav_AccountSwitcher_Button']").count() > 0 or
                self.page.locator("nav[role='navigation']").count() > 0):
                print(f"Account {username}: Healthy.")
                return "Healthy"
            
            # Fallback: check if we can see the tweet input box
            if self.page.locator("div[data-testid='tweetTextarea_0']").count() > 0:
                 print(f"Account {username}: Healthy (Found Input).")
                 return "Healthy"
            
            # Fallback
            print(f"Account {username}: Status Unknown (Might be loading issue).")
            # If we are on home but failed counters, it might be just slow. 
            # If URL is home, assume Healthy-ish?
            if "home" in self.page.url:
                 return "Healthy"

            return "Unknown"

        except Exception as e:
            print(f"Error checking status for {username}: {e}")
            return "Error"

    def close(self):
        try:
            if self.context: self.context.close()
            if self.browser: self.browser.close()
        except Exception as e:
            print(f"Error closing browser elements: {e}")
        finally:
            if self.playwright: 
                try:
                    self.playwright.stop()
                except:
                    pass
            self.playwright = None
            self.browser = None
            self.context = None
            self.page = None
            self.page = None
