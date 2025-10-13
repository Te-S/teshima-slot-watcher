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
        # Multiple museums to monitor
        self.museums = {
            'teshima': {
                'name': 'Teshima Art Museum',
                'url': 'https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/185773',
                'iframe_url': 'https://web.admin-benesse-artsite.com/calendar/5?language=jpn'
            },
            'chichu': {
                'name': 'Chichu Art Museum',
                'url': 'https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/176695?language=eng',
                'iframe_url': 'https://web.admin-benesse-artsite.com/calendar/6?language=eng'
            },
            'sugimoto': {
                'name': 'Hiroshi Sugimoto Gallery: Time Corridors',
                'url': 'https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/185771?language=eng',
                'iframe_url': 'https://web.admin-benesse-artsite.com/calendar/7?language=eng'
            }
        }
        
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
        """Check ticket availability for all museums"""
        try:
            logging.info("Checking ticket availability for all museums...")
            
            all_availability_data = {}
            
            # Check each museum
            for museum_id, museum_info in self.museums.items():
                logging.info(f"Checking {museum_info['name']}...")
                
                try:
                    # Try static parsing first
                    availability_data = self.check_museum_static(museum_info)
                    
                    # If no data found with static parsing, try Selenium
                    if not availability_data:
                        logging.info(f"No data found with static parsing for {museum_info['name']}, trying Selenium...")
                        selenium_data = self.check_museum_selenium(museum_info)
                        availability_data.update(selenium_data)
                    
                    # Add museum prefix to keys
                    museum_data = {}
                    for date_str, status in availability_data.items():
                        museum_data[f"{museum_id}_{date_str}"] = status
                    
                    all_availability_data.update(museum_data)
                    logging.info(f"Found {len(availability_data)} dates for {museum_info['name']}")
                    
                except Exception as e:
                    logging.error(f"Error checking {museum_info['name']}: {str(e)}")
                    continue
            
            # In test mode, always send test email
            if test_mode:
                logging.info("🧪 Test mode: Sending test email with current availability data")
                self.send_test_email(all_availability_data)
            else:
                # Check for changes in availability
                self.check_for_changes(all_availability_data)
            
            # Update last known state
            self.last_availability = all_availability_data.copy()
            self.save_state(all_availability_data)
            
        except Exception as e:
            logging.error(f"Error checking availability: {str(e)}")
    
    def check_museum_static(self, museum_info):
        """Check museum availability using static HTML parsing"""
        try:
            # Make request to the iframe URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': museum_info['url']
            }
            
            response = requests.get(museum_info['iframe_url'], headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse calendar data
            return self.parse_calendar(soup)
            
        except Exception as e:
            logging.error(f"Static parsing failed for {museum_info['name']}: {str(e)}")
            return {}
    
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
    
    def check_museum_selenium(self, museum_info):
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
            
            # Initialize the driver with proper ChromeDriver path for GitHub Actions
            try:
                # Try to find the actual chromedriver binary
                driver_path = ChromeDriverManager().install()
                # Fix the path if it points to a text file
                if 'THIRD_PARTY_NOTICES' in driver_path:
                    import os
                    driver_dir = os.path.dirname(driver_path)
                    # Look for the actual chromedriver binary
                    for file in os.listdir(driver_dir):
                        if file.startswith('chromedriver') and not file.endswith('.txt'):
                            driver_path = os.path.join(driver_dir, file)
                            break
                
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                logging.error(f"ChromeDriver setup failed: {e}")
                # Fallback: try without explicit path
                driver = webdriver.Chrome(options=chrome_options)
            
            try:
                # Navigate to the iframe URL directly
                driver.get(museum_info['iframe_url'])
                
                # Wait for the page to load and JavaScript to execute
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Wait additional time for JavaScript to load calendar data
                time.sleep(10)  # Increased wait for GitHub Actions
                
                # Look for calendar elements to ensure they're loaded
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "td, .day, [class*='day'], [class*='date']"))
                    )
                    logging.info("Calendar elements found - JavaScript loaded successfully")
                except:
                    logging.warning("Calendar elements not found - may need more time to load")
                
                # Wait a bit more for JavaScript to load calendar
                time.sleep(10)  # Increased wait for GitHub Actions
                
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
                        
                        # Method 2: Check for child elements with price-day classes
                        if status == 'unknown':
                            # Look for child elements with price-day classes
                            price_elements = element.find_elements(By.CSS_SELECTOR, ".price-day")
                            
                            # Check for specific status classes in priority order
                            for price_elem in price_elements:
                                price_classes = price_elem.get_attribute('class') or ''
                                if 'one-left' in price_classes:
                                    status = 'few_left'
                                    break
                                elif 'aval' in price_classes or 'available' in price_classes:
                                    status = 'available'
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
                                ".price-day.one-left",
                                ".price-day.aval",
                                ".price-day.sold-out",
                                ".closed-section"
                            ]
                            for status_selector in status_selectors:
                                if element.find_elements(By.CSS_SELECTOR, status_selector):
                                    if 'one-left' in status_selector:
                                        status = 'few_left'
                                    elif 'aval' in status_selector:
                                        status = 'available'
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
        for date_key, status in current_availability.items():
            if status in ['available', 'few_left']:
                try:
                    # Extract date from museum-prefixed key (e.g., "teshima_2025-10-26" -> "2025-10-26")
                    if '_' in date_key:
                        date_str = date_key.split('_', 1)[1]  # Get everything after first underscore
                    else:
                        date_str = date_key
                    
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    available_dates.append((parsed_date, status, date_key))
                except ValueError as e:
                    logging.warning(f"Could not parse date from key '{date_key}': {e}")
                    continue
        
        logging.info(f"Found {len(available_dates)} available dates in current calendar")
        
        # Check if any available dates are new (weren't available before)
        new_available_dates = []
        for parsed_date, status, original_key in available_dates:
            # Check both the original key and the date-only key for previous status
            previous_status_original = self.last_availability.get(original_key, 'unknown')
            date_str = parsed_date.strftime('%Y-%m-%d')
            previous_status_date = self.last_availability.get(date_str, 'unknown')
            
            # Use the more specific previous status (original key takes precedence)
            previous_status = previous_status_original if previous_status_original != 'unknown' else previous_status_date
            
            logging.info(f"Date {date_str}: current={status}, previous={previous_status}")
            
            # If this date wasn't available before, it's new
            if previous_status not in ['available', 'few_left']:
                new_available_dates.append((parsed_date, status))
                logging.info(f"NEW availability detected: {date_str} changed from {previous_status} to {status}")
            else:
                logging.info(f"EXISTING availability: {date_str} remains {status}")
        
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
        """Send a test email with current availability status for all museums"""
        if not self.sendgrid_api_key:
            logging.error("SendGrid API key not found. Please set SENDGRID_API_KEY environment variable.")
            return
        
        try:
            # Organize data by museum
            museum_data = {}
            for key, status in availability_data.items():
                if '_' in key:
                    museum_id, date_str = key.split('_', 1)
                    if museum_id not in museum_data:
                        museum_data[museum_id] = {}
                    museum_data[museum_id][date_str] = status
            
            # Create museum sections
            museum_sections = []
            total_available = 0
            total_few_left = 0
            total_sold_out = 0
            total_closed = 0
            
            for museum_id, museum_info in self.museums.items():
                museum_name = museum_info['name']
                museum_url = museum_info['url']
                
                if museum_id in museum_data:
                    dates = museum_data[museum_id]
                    
                    # Count statuses for this museum
                    available_count = sum(1 for s in dates.values() if s == 'available')
                    few_left_count = sum(1 for s in dates.values() if s == 'few_left')
                    sold_out_count = sum(1 for s in dates.values() if s == 'sold_out')
                    closed_count = sum(1 for s in dates.values() if s == 'closed')
                    
                    total_available += available_count
                    total_few_left += few_left_count
                    total_sold_out += sold_out_count
                    total_closed += closed_count
                    
                    # Create status lines for this museum
                    status_lines = []
                    for date_str, status in sorted(dates.items()):
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
                    
                    museum_section = f"""
                    <h3>🏛️ {museum_name}</h3>
                    <p><strong>URL:</strong> <a href="{museum_url}">{museum_url}</a></p>
                    <p><strong>Summary:</strong> ✅ {available_count} | ⚠️ {few_left_count} | ❌ {sold_out_count} | 🚫 {closed_count}</p>
                    <ul>
                        {''.join(status_lines)}
                    </ul>
                    """
                    museum_sections.append(museum_section)
                else:
                    museum_section = f"""
                    <h3>🏛️ {museum_name}</h3>
                    <p><strong>URL:</strong> <a href="{museum_url}">{museum_url}</a></p>
                    <p><strong>Status:</strong> ❓ No data found</p>
                    """
                    museum_sections.append(museum_section)
            
            subject = f"🧪 Art Museum Slot Watcher - Test Report ({datetime.now(JST).strftime('%Y-%m-%d %H:%M')})"
            
            html_content = f"""
            <html>
            <body>
                <h2>🧪 Art Museum Slot Watcher Test Report</h2>
                <p><strong>Test Time:</strong> {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Monitoring:</strong> {len(self.museums)} museums</p>
                
                {''.join(museum_sections)}
                
                <h3>📊 Overall Summary:</h3>
                <p>Total dates found: {len(availability_data)}</p>
                <p>✅ Available dates: {total_available}</p>
                <p>⚠️ Few left dates: {total_few_left}</p>
                <p>❌ Sold out dates: {total_sold_out}</p>
                <p>🚫 Closed dates: {total_closed}</p>
                
                <hr>
                <p><small>This is a test email from your Art Museum Slot Watcher to verify SendGrid is working properly.</small></p>
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
        logging.info("Starting Art Museum Slot Watcher check...")
        logging.info(f"Monitoring {len(self.museums)} museums for available dates")
        logging.info(f"Target email: {self.target_email}")
        
        if test_mode:
            logging.info("🧪 Running in TEST MODE - will send test email with all calendar data")
        
        # Run the check
        self.check_availability(test_mode=test_mode)
        
        logging.info("Art Museum Slot Watcher check completed.")

if __name__ == "__main__":
    import sys
    
    # Check for test mode argument
    test_mode = len(sys.argv) > 1 and sys.argv[1] == '--test'
    
    watcher = SlotWatcher()
    watcher.run(test_mode=test_mode)
