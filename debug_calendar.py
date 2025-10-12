#!/usr/bin/env python3
"""
Debug script to inspect the Teshima Art Museum calendar HTML structure
"""

import requests
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def debug_calendar():
    """Debug the calendar HTML structure"""
    url = "https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/185773"
    
    print("🔍 Debugging Teshima Art Museum Calendar")
    print("=" * 50)
    
    try:
        # Fetch the page
        print(f"📡 Fetching: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Page loaded successfully (Status: {response.status_code})")
        print(f"📄 Content length: {len(response.text)} characters")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Save full HTML for inspection
        with open('debug_page_source.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("💾 Saved full HTML to debug_page_source.html")
        
        # Look for calendar-related elements
        print("\n🔍 Searching for calendar elements...")
        
        # Search for various calendar-related selectors
        calendar_selectors = [
            '.calendar',
            '.body-calendar-jp',
            '.item',
            '.price-day',
            '.aval',
            '.one-left',
            '.sold-out',
            '.closed-section',
            '[class*="calendar"]',
            '[class*="day"]',
            '[class*="date"]'
        ]
        
        for selector in calendar_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"✅ Found {len(elements)} elements with selector: {selector}")
                for i, elem in enumerate(elements[:3]):  # Show first 3
                    print(f"   {i+1}. {elem.name} - Classes: {elem.get('class', [])}")
                    print(f"      Text: {elem.get_text(strip=True)[:100]}...")
            else:
                print(f"❌ No elements found with selector: {selector}")
        
        # Look for JavaScript variables
        print("\n🔍 Searching for JavaScript calendar data...")
        scripts = soup.find_all('script')
        calendar_js_found = False
        
        for i, script in enumerate(scripts):
            if script.string and any(keyword in script.string.lower() for keyword in ['calendar', 'date', 'availability', 'ticket']):
                print(f"📜 Script {i+1} contains calendar-related content:")
                print(f"   Length: {len(script.string)} characters")
                print(f"   Preview: {script.string[:200]}...")
                calendar_js_found = True
        
        if not calendar_js_found:
            print("❌ No JavaScript calendar data found")
        
        # Look for any elements with numbers (potential dates)
        print("\n🔍 Searching for date-like elements...")
        all_elements = soup.find_all(['div', 'span', 'td', 'li'])
        date_elements = []
        
        for elem in all_elements:
            text = elem.get_text(strip=True)
            if text.isdigit() and 1 <= int(text) <= 31:
                classes = elem.get('class', [])
                date_elements.append((text, classes, elem.name))
        
        if date_elements:
            print(f"✅ Found {len(date_elements)} potential date elements:")
            for text, classes, tag in date_elements[:10]:  # Show first 10
                print(f"   {tag} with text '{text}' - Classes: {classes}")
        else:
            print("❌ No date-like elements found")
        
        print("\n🎯 Debug complete! Check debug_page_source.html for full HTML structure.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    debug_calendar()
