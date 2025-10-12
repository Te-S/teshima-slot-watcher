import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SlotWatcher:
    def __init__(self):
        self.url = "https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/185773"
        self.target_email = os.getenv('TARGET_EMAIL', 'yli881118@gmail.com')
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        self.target_dates = [
            date(2024, 10, 20),
            date(2024, 10, 21), 
            date(2024, 10, 22),
            date(2024, 10, 23),
            date(2024, 10, 24)
        ]
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
        
    def check_availability(self):
        """Check ticket availability for target dates"""
        try:
            logging.info("Checking ticket availability...")
            
            # Make request to the page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find calendar elements - we need to inspect the actual page structure
            availability_data = self.parse_calendar(soup)
            
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
                    
                    # Try to determine the month and year
                    # This is tricky since we need to infer from context
                    # For now, we'll assume current year and try to match October dates
                    current_year = datetime.now().year
                    
                    # Look for October dates (month 10)
                    # We need to be more sophisticated about this
                    # For now, let's check if this could be October 2024
                    if day_num in [20, 21, 22, 23, 24]:
                        # This could be our target date
                        potential_date = date(current_year, 10, day_num)
                        
                        # Only include if it's in our target dates
                        if potential_date in self.target_dates:
                            availability_data[potential_date.strftime('%Y-%m-%d')] = status
                            logging.info(f"Found date {potential_date}: {status}")
        
        # Also look for any JavaScript data that might contain calendar information
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'calendar' in script.string.lower():
                # Try to extract calendar data from JavaScript
                # This would need more sophisticated parsing
                pass
        
        logging.info(f"Parsed availability data: {availability_data}")
        return availability_data
    
    def check_for_changes(self, current_availability):
        """Check if availability has changed and send notifications"""
        for target_date in self.target_dates:
            date_str = target_date.strftime('%Y-%m-%d')
            
            # Check if this date has become available
            if date_str in current_availability:
                current_status = current_availability[date_str]
                previous_status = self.last_availability.get(date_str, 'unknown')
                
                # If status changed to available or few left, send notification
                if (current_status in ['available', 'few_left'] and 
                    previous_status not in ['available', 'few_left']):
                    
                    self.send_notification(target_date, current_status)
    
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
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr>
                <p><a href="{self.url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Book Now</a></p>
                <p><small>This is an automated notification from your Slot Watcher.</small></p>
            </body>
            </html>
            """
            
            message = Mail(
                from_email='noreply@slotwatcher.com',
                to_emails=self.target_email,
                subject=subject,
                html_content=html_content
            )
            
            sg = SendGridAPIClient(api_key=self.sendgrid_api_key)
            response = sg.send(message)
            
            logging.info(f"Notification sent for {target_date} - Status: {status}")
            
        except Exception as e:
            logging.error(f"Failed to send notification: {str(e)}")
    
    def run(self):
        """Run a single check (for GitHub Actions)"""
        logging.info("Starting Slot Watcher check...")
        logging.info(f"Monitoring dates: {[d.strftime('%Y-%m-%d') for d in self.target_dates]}")
        logging.info(f"Target email: {self.target_email}")
        
        # Run the check
        self.check_availability()
        
        logging.info("Slot Watcher check completed.")

if __name__ == "__main__":
    watcher = SlotWatcher()
    watcher.run()
