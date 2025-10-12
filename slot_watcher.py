import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timezone, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import logging
import json
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# JST timezone (UTC+9)
JST = timezone(timedelta(hours=9))

class SlotWatcher:
    def __init__(self):
        self.url = "https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/185773"
        self.target_email = os.getenv('TARGET_EMAIL', 'yli881118@gmail.com')
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        # No specific target dates - we'll monitor the entire calendar
        self.target_dates = []
        self.state_file = 'availability_state.json'
        self.last_availability = self.load_state()
    
    def load_state(self):
        """Load previous availability state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.warning(f"Could not load state file: {e}")
        return {}
    
    def save_state(self, state):
        """Save current availability state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logging.error(f"Could not save state file: {e}")
        
    def check_availability(self, test_mode=False):
        """Check ticket availability by fetching the calendar iframe directly"""
        try:
            logging.info("Checking ticket availability...")
            
            # The calendar is loaded in an iframe, so we need to fetch the iframe URL directly
            iframe_url = "https://web.admin-benesse-artsite.com/calendar/5?language=jpn"
            logging.info(f"Fetching calendar iframe: {iframe_url}")
            
            # Make request to the iframe URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': self.url
            }
            
            response = requests.get(iframe_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to parse calendar data
            availability_data = self.parse_calendar(soup)
            
            # If no data found with static parsing, try Selenium
            if not availability_data:
                logging.info("No data found with static parsing, trying Selenium...")
                selenium_data = self.check_availability_with_selenium()
                availability_data.update(selenium_data)
            
            # In test mode, always send test email
            if test_mode:
                logging.info("🧪 Test mode: Sending test email with current availability data")
                self.send_test_email(availability_data)
            else:
                # Check for changes in availability
                self.check_for_changes(availability_data)
            
            # Update last known state
            self.last_availability = availability_data.copy()
            self.save_state(availability_data)
            
        except Exception as e:
            logging.error(f"Error checking availability: {str(e)}")
    
    def parse_calendar(self, soup):
        """Parse the calendar to extract availability information"""
        availability_data = {}
        
        # First, try to extract calendar data from JavaScript
        js_data = self.extract_calendar_from_js(soup)
        if js_data:
            availability_data.update(js_data)
            logging.info(f"Found calendar data in JavaScript: {js_data}")
        
        # Also try to parse static HTML elements (fallback)
        html_data = self.parse_static_calendar(soup)
        if html_data:
            availability_data.update(html_data)
            logging.info(f"Found calendar data in HTML: {html_data}")
        
        logging.info(f"Total parsed availability data: {availability_data}")
        return availability_data
    
    def extract_calendar_from_js(self, soup):
        """Extract calendar data from JavaScript variables"""
        availability_data = {}
        
        scripts = soup.find_all('script')
        for script in scripts:
            if not script.string:
                continue
                
            script_content = script.string
            
            # Look for calendar-related data structures
            # Common patterns: window.calendarData, calendarData, etc.
            import re
            
            # Try to find calendar data in various formats
            patterns = [
                r'calendarData\s*[:=]\s*({[^}]+})',
                r'window\.calendarData\s*[:=]\s*({[^}]+})',
                r'calendar\s*[:=]\s*({[^}]+})',
                r'window\.calendar\s*[:=]\s*({[^}]+})',
                r'data\s*[:=]\s*({[^}]+})',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                for match in matches:
                    try:
                        # Try to parse as JSON-like structure
                        import json
                        # Clean up the match to make it valid JSON
                        cleaned = match.replace("'", '"').replace('True', 'true').replace('False', 'false')
                        data = json.loads(cleaned)
                        
                        # Look for date/availability information
                        availability_data.update(self.parse_js_calendar_data(data))
                        
                    except (json.JSONDecodeError, ValueError):
                        # If not JSON, try to extract date patterns manually
                        availability_data.update(self.extract_dates_from_text(match))
        
        return availability_data
    
    def parse_js_calendar_data(self, data):
        """Parse JavaScript calendar data structure"""
        availability_data = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                # Look for date-like keys
                if self.is_date_key(key):
                    date_obj = self.parse_date_key(key)
                    if date_obj and date_obj in self.target_dates:
                        status = self.determine_status_from_value(value)
                        if status:
                            availability_data[date_obj.strftime('%Y-%m-%d')] = status
        
        return availability_data
    
    def is_date_key(self, key):
        """Check if a key represents a date"""
        import re
        # Look for patterns like "2024-10-20", "10/20", "20241020", etc.
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # 2024-10-20
            r'\d{2}/\d{2}',        # 10/20
            r'\d{8}',              # 20241020
            r'october.*20\d{2}',   # october 2024
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, key.lower()):
                return True
        return False
    
    def parse_date_key(self, key):
        """Parse a date key into a date object"""
        import re
        from datetime import datetime
        
        try:
            # Try different date formats
            formats = [
                '%Y-%m-%d',        # 2024-10-20
                '%m/%d',           # 10/20
                '%Y%m%d',          # 20241020
            ]
            
            for fmt in formats:
                try:
                    parsed = datetime.strptime(key, fmt)
                    # If no year, assume 2024
                    if parsed.year == 1900:
                        parsed = parsed.replace(year=2024)
                    return parsed.date()
                except ValueError:
                    continue
            
            # Try regex extraction
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', key)
            if match:
                year, month, day = map(int, match.groups())
                return date(year, month, day)
                
        except Exception as e:
            logging.warning(f"Could not parse date key '{key}': {e}")
        
        return None
    
    def determine_status_from_value(self, value):
        """Determine availability status from a value"""
        if isinstance(value, str):
            value_lower = value.lower()
            if any(word in value_lower for word in ['available', 'open', 'circle']):
                return 'available'
            elif any(word in value_lower for word in ['few', 'limited', 'triangle']):
                return 'few_left'
            elif any(word in value_lower for word in ['sold', 'out', 'cross', 'closed']):
                return 'sold_out'
            elif 'closed' in value_lower:
                return 'closed'
        elif isinstance(value, bool):
            return 'available' if value else 'sold_out'
        elif isinstance(value, int):
            if value > 0:
                return 'available' if value > 5 else 'few_left'
            else:
                return 'sold_out'
        
        return None
    
    def extract_dates_from_text(self, text):
        """Extract date information from text patterns"""
        availability_data = {}
        import re
        
        # Look for date patterns with status indicators
        patterns = [
            r'(\d{4}-\d{2}-\d{2})["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
            r'(\d{2}/\d{2})["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for date_str, status_str in matches:
                try:
                    date_obj = self.parse_date_key(date_str)
                    if date_obj and date_obj in self.target_dates:
                        status = self.determine_status_from_value(status_str)
                        if status:
                            availability_data[date_obj.strftime('%Y-%m-%d')] = status
                except Exception as e:
                    logging.warning(f"Error parsing date from text: {e}")
        
        return availability_data
    
    def parse_static_calendar(self, soup):
        """Parse static HTML calendar elements (fallback method)"""
        availability_data = {}
        
        # Look for calendar items with availability information
        calendar_items = soup.find_all('div', class_='body-calendar-jp')
        
        for calendar_row in calendar_items:
            items = calendar_row.find_all('div', class_='item')
            
            for item in items:
                # Extract date information
                title_day = item.find('div', class_='title-day')
                if not title_day:
                    continue
                
                # Get the day number
                day_text = title_day.get_text(strip=True)
                if not day_text.isdigit():
                    continue
                
                day_num = int(day_text)
                
                # Check for availability status
                price_day = item.find('div', class_='price-day')
                if price_day:
                    # Check for availability classes
                    if 'aval' in price_day.get('class', []):
                        status = 'available'  # Circle - Available
                    elif 'one-left' in price_day.get('class', []):
                        status = 'few_left'   # Triangle - Only a few left
                    elif 'sold-out' in price_day.get('class', []):
                        status = 'sold_out'   # Cross - Sold out
                    else:
                        status = 'unknown'
                    
                    # Check for closed status
                    closed_section = item.find('div', class_='closed-section')
                    if closed_section:
                        status = 'closed'
                    
                    # Try to determine the month and year from context
                    # Look for month/year indicators in the calendar
                    month_year = self.extract_month_year_from_context(soup)
                    if month_year:
                        year, month = month_year
                        potential_date = date(year, month, day_num)
                        
                        # Include all dates found in the calendar
                        availability_data[potential_date.strftime('%Y-%m-%d')] = status
                        logging.info(f"Found static date {potential_date}: {status}")
        
        return availability_data
    
    def extract_month_year_from_context(self, soup):
        """Extract month and year from calendar context"""
        # Look for month/year indicators in the calendar
        month_year_elements = soup.find_all(['span', 'div'], class_=lambda x: x and any(
            keyword in str(x).lower() for keyword in ['month', 'year', 'calendar-title']
        ))
        
        for element in month_year_elements:
            text = element.get_text(strip=True)
            # Look for patterns like "October 2024", "2024年10月", etc.
            import re
            
            # English patterns
            match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})', text.lower())
            if match:
                month_name, year = match.groups()
                month_map = {
                    'january': 1, 'february': 2, 'march': 3, 'april': 4,
                    'may': 5, 'june': 6, 'july': 7, 'august': 8,
                    'september': 9, 'october': 10, 'november': 11, 'december': 12
                }
                return int(year), month_map[month_name]
            
            # Japanese patterns
            match = re.search(r'(\d{4})年(\d{1,2})月', text)
            if match:
                year, month = map(int, match.groups())
                return year, month
        
        # Default to current year and October if we can't determine
        current_year = datetime.now().year
        return current_year, 10
    
    def check_availability_with_selenium(self):
        """Alternative method using Selenium for JavaScript-heavy pages"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            logging.info("Attempting to use Selenium for JavaScript-heavy page...")
            
            # Set up Chrome options for headless mode
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Initialize the driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            try:
                # Navigate to the iframe URL directly
                iframe_url = "https://web.admin-benesse-artsite.com/calendar/5?language=jpn"
                driver.get(iframe_url)
                
                # Wait for the page to load and JavaScript to execute
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Wait additional time for JavaScript to load calendar data
                time.sleep(5)
                
                # Look for calendar elements to ensure they're loaded
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "td, .day, [class*='day'], [class*='date']"))
                    )
                    logging.info("Calendar elements found - JavaScript loaded successfully")
                except:
                    logging.warning("Calendar elements not found - may need more time to load")
                
                # Wait a bit more for JavaScript to load calendar
                time.sleep(5)
                
                # Try to find calendar elements with multiple selectors
                calendar_selectors = [
                    ".body-calendar-jp .item",
                    "button.item",
                    ".item",
                    "td",
                    ".day",
                    "[class*='day']",
                    "[class*='date']",
                    ".calendar td",
                    ".calendar .day"
                ]
                
                calendar_elements = []
                for selector in calendar_selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        calendar_elements = elements
                        logging.info(f"Found {len(elements)} calendar elements with selector: {selector}")
                        break
                
                if not calendar_elements:
                    logging.warning("No calendar elements found with any selector")
                    return {}
                
                availability_data = {}
                
                for element in calendar_elements:
                    try:
                        # Get the day number
                        day_element = element.find_element(By.CSS_SELECTOR, ".title-day")
                        day_text = day_element.text.strip()
                        
                        if not day_text.isdigit():
                            continue
                        
                        day_num = int(day_text)
                        
                        # Check for availability status with multiple approaches
                        status = 'unknown'
                        
                        # Method 1: Check CSS classes on the element itself
                        element_classes = element.get_attribute('class') or ''
                        if 'aval' in element_classes or 'available' in element_classes:
                            status = 'available'
                        elif 'one-left' in element_classes or 'few' in element_classes:
                            status = 'few_left'
                        elif 'sold-out' in element_classes or 'sold' in element_classes:
                            status = 'sold_out'
                        elif 'closed' in element_classes:
                            status = 'closed'
                        
                        # Method 2: Check for sibling elements with price-day classes
                        if status == 'unknown':
                            # Look for sibling elements with price-day classes
                            parent = element.find_element(By.XPATH, "..")
                            price_elements = parent.find_elements(By.CSS_SELECTOR, ".price-day")
                            for price_elem in price_elements:
                                price_classes = price_elem.get_attribute('class') or ''
                                if 'aval' in price_classes or 'available' in price_classes:
                                    status = 'available'
                                    break
                                elif 'one-left' in price_classes:
                                    status = 'few_left'
                                    break
                                elif 'sold-out' in price_classes:
                                    status = 'sold_out'
                                    break
                                elif 'closed' in price_classes:
                                    status = 'closed'
                                    break
                        
                        # Method 3: Check for child elements with status classes
                        if status == 'unknown':
                            status_selectors = [
                                ".price-day.aval",
                                ".price-day.one-left", 
                                ".price-day.sold-out",
                                ".closed-section"
                            ]
                            for status_selector in status_selectors:
                                if element.find_elements(By.CSS_SELECTOR, status_selector):
                                    if 'aval' in status_selector:
                                        status = 'available'
                                    elif 'one-left' in status_selector:
                                        status = 'few_left'
                                    elif 'sold-out' in status_selector:
                                        status = 'sold_out'
                                    elif 'closed' in status_selector:
                                        status = 'closed'
                                    break
                        
                        # Method 4: Check element text for status indicators
                        if status == 'unknown':
                            element_text = element.text.lower()
                            if any(word in element_text for word in ['available', 'open', 'circle']):
                                status = 'available'
                            elif any(word in element_text for word in ['few', 'limited', 'triangle']):
                                status = 'few_left'
                            elif any(word in element_text for word in ['sold', 'out', 'cross', 'closed']):
                                status = 'sold_out'
                        
                        # Try to determine the month/year from page context
                        month_year = self.extract_month_year_from_selenium(driver)
                        if month_year:
                            year, month = month_year
                            potential_date = date(year, month, day_num)
                            
                            # Include all dates found in the calendar
                            availability_data[potential_date.strftime('%Y-%m-%d')] = status
                            logging.info(f"Found Selenium date {potential_date}: {status}")
                    
                    except Exception as e:
                        logging.warning(f"Error processing calendar element: {e}")
                        continue
                
                return availability_data
                
            finally:
                driver.quit()
                
        except ImportError:
            logging.warning("Selenium not available, skipping Selenium-based parsing")
            return {}
        except Exception as e:
            logging.error(f"Selenium-based parsing failed: {e}")
            return {}
    
    def extract_month_year_from_selenium(self, driver):
        """Extract month and year from Selenium driver"""
        try:
            # Look for month/year indicators
            month_year_elements = driver.find_elements(By.CSS_SELECTOR, ".title-calendar-jp, .year-calendar-jp, .month-calendar-jp")
            
            for element in month_year_elements:
                text = element.text.strip()
                import re
                
                # English patterns
                match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})', text.lower())
                if match:
                    month_name, year = match.groups()
                    month_map = {
                        'january': 1, 'february': 2, 'march': 3, 'april': 4,
                        'may': 5, 'june': 6, 'july': 7, 'august': 8,
                        'september': 9, 'october': 10, 'november': 11, 'december': 12
                    }
                    return int(year), month_map[month_name]
                
                # Japanese patterns
                match = re.search(r'(\d{4})年(\d{1,2})月', text)
                if match:
                    year, month = map(int, match.groups())
                    return year, month
            
            # Default to current year and October
            current_year = datetime.now(JST).year
            return current_year, 10
            
        except Exception as e:
            logging.warning(f"Could not extract month/year from Selenium: {e}")
            current_year = datetime.now(JST).year
            return current_year, 10
    
    def check_for_changes(self, current_availability):
        """Check if availability has changed and send notifications for any available dates"""
        available_dates = []
        
        # Find all available dates in the current calendar
        for date_str, status in current_availability.items():
            if status in ['available', 'few_left']:
                try:
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    available_dates.append((parsed_date, status))
                except ValueError:
                    continue
        
        # Check if any available dates are new (weren't available before)
        new_available_dates = []
        for parsed_date, status in available_dates:
            date_str = parsed_date.strftime('%Y-%m-%d')
            previous_status = self.last_availability.get(date_str, 'unknown')
            
            # If this date wasn't available before, it's new
            if previous_status not in ['available', 'few_left']:
                new_available_dates.append((parsed_date, status))
        
        # Send notifications for new available dates
        if new_available_dates:
            logging.info(f"Found {len(new_available_dates)} new available dates!")
            for parsed_date, status in new_available_dates:
                self.send_notification(parsed_date, status)
        else:
            logging.info("No new available dates found")
    
    def send_notification(self, target_date, status):
        """Send email notification about availability"""
        if not self.sendgrid_api_key:
            logging.error("SendGrid API key not found. Please set SENDGRID_API_KEY environment variable.")
            return
        
        try:
            status_text = {
                'available': 'Available for purchase',
                'few_left': 'Only a few left',
                'sold_out': 'Sold out',
                'closed': 'Closed'
            }.get(status, status)
            
            subject = f"🎫 Teshima Art Museum Ticket Available - {target_date.strftime('%B %d, %Y')}"
            
            html_content = f"""
            <html>
            <body>
                <h2>🎫 Teshima Art Museum Ticket Alert!</h2>
                <p><strong>Date:</strong> {target_date.strftime('%B %d, %Y')}</p>
                <p><strong>Status:</strong> {status_text}</p>
                <p><strong>Time:</strong> {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr>
                <p><a href="{self.url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Book Now</a></p>
                <p><small>This is an automated notification from your Slot Watcher.</small></p>
            </body>
            </html>
            """
            
            message = Mail(
                from_email='notification@starcape.online',  # Use verified sender email
                to_emails=self.target_email,
                subject=subject,
                html_content=html_content
            )
            
            sg = SendGridAPIClient(api_key=self.sendgrid_api_key)
            response = sg.send(message)
            
            logging.info(f"Notification sent for {target_date} - Status: {status}")
            
        except Exception as e:
            logging.error(f"Failed to send notification: {str(e)}")
    
    def send_test_email(self, availability_data):
        """Send a test email with current availability status for all dates found in calendar"""
        if not self.sendgrid_api_key:
            logging.error("SendGrid API key not found. Please set SENDGRID_API_KEY environment variable.")
            return
        
        try:
            # Create a comprehensive status report for all dates found
            status_lines = []
            available_count = 0
            few_left_count = 0
            sold_out_count = 0
            closed_count = 0
            
            for date_str, status in availability_data.items():
                try:
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    date_display = parsed_date.strftime('%B %d, %Y')
                except ValueError:
                    date_display = date_str
                
                status_text = {
                    'available': '✅ Available for purchase',
                    'few_left': '⚠️ Only a few left',
                    'sold_out': '❌ Sold out',
                    'closed': '🚫 Closed'
                }.get(status, f'❓ Unknown: {status}')
                
                status_lines.append(f"<li><strong>{date_display}</strong>: {status_text}</li>")
                
                # Count by status
                if status == 'available':
                    available_count += 1
                elif status == 'few_left':
                    few_left_count += 1
                elif status == 'sold_out':
                    sold_out_count += 1
                elif status == 'closed':
                    closed_count += 1
            
            subject = f"🧪 Teshima Art Museum Slot Watcher - Test Report ({datetime.now(JST).strftime('%Y-%m-%d %H:%M')})"
            
            html_content = f"""
            <html>
            <body>
                <h2>🧪 Slot Watcher Test Report</h2>
                <p><strong>Test Time:</strong> {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Monitoring URL:</strong> <a href="{self.url}">{self.url}</a></p>
                
                <h3>📅 Calendar Status:</h3>
                <ul>
                    {''.join(status_lines)}
                </ul>
                
                <h3>📊 Summary:</h3>
                <p>Total dates found: {len(availability_data)}</p>
                <p>✅ Available dates: {available_count}</p>
                <p>⚠️ Few left dates: {few_left_count}</p>
                <p>❌ Sold out dates: {sold_out_count}</p>
                <p>🚫 Closed dates: {closed_count}</p>
                
                <hr>
                <p><small>This is a test email from your Teshima Art Museum Slot Watcher to verify SendGrid is working properly.</small></p>
                <p><small>If you received this email, SendGrid integration is working correctly! 🎉</small></p>
            </body>
            </html>
            """
            
            message = Mail(
                from_email='notification@starcape.online',  # Use verified sender email
                to_emails=self.target_email,
                subject=subject,
                html_content=html_content
            )
            
            sg = SendGridAPIClient(api_key=self.sendgrid_api_key)
            response = sg.send(message)
            
            logging.info("Test email sent successfully!")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send test email: {str(e)}")
            return False
    
    def run(self, test_mode=False):
        """Run a single check (for GitHub Actions)"""
        logging.info("Starting Slot Watcher check...")
        logging.info("Monitoring entire calendar for available dates")
        logging.info(f"Target email: {self.target_email}")
        
        if test_mode:
            logging.info("🧪 Running in TEST MODE - will send test email with all calendar data")
        
        # Run the check
        self.check_availability(test_mode=test_mode)
        
        logging.info("Slot Watcher check completed.")

if __name__ == "__main__":
    import sys
    
    # Check for test mode argument
    test_mode = len(sys.argv) > 1 and sys.argv[1] == '--test'
    
    watcher = SlotWatcher()
    watcher.run(test_mode=test_mode)
