#!/usr/bin/env python3
"""
Test script to verify the slot watcher parsing logic
"""

import requests
from bs4 import BeautifulSoup
from slot_watcher import SlotWatcher
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_parsing():
    """Test the calendar parsing logic"""
    watcher = SlotWatcher()
    
    try:
        print("Testing calendar parsing...")
        
        # Make request to the page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(watcher.url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Test the parsing
        availability_data = watcher.parse_calendar(soup)
        
        print(f"\n=== PARSING RESULTS ===")
        print(f"Found availability data: {availability_data}")
        
        # Check for our target dates
        for target_date in watcher.target_dates:
            date_str = target_date.strftime('%Y-%m-%d')
            if date_str in availability_data:
                print(f"✅ {target_date.strftime('%B %d, %Y')}: {availability_data[date_str]}")
            else:
                print(f"❌ {target_date.strftime('%B %d, %Y')}: Not found")
        
        # Test change detection
        print(f"\n=== CHANGE DETECTION TEST ===")
        watcher.check_for_changes(availability_data)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_parsing()
