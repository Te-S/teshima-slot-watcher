#!/usr/bin/env python3
"""
Debug script to test the iframe URL directly
"""

import requests
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def debug_iframe():
    """Debug the iframe calendar directly"""
    iframe_url = "https://web.admin-benesse-artsite.com/calendar/5?language=jpn"
    main_url = "https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/185773"
    
    print("🔍 Debugging Calendar Iframe")
    print("=" * 50)
    
    try:
        # Fetch the iframe content
        print(f"📡 Fetching iframe: {iframe_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': main_url
        }
        response = requests.get(iframe_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Iframe loaded successfully (Status: {response.status_code})")
        print(f"📄 Content length: {len(response.text)} characters")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Save iframe HTML for inspection
        with open('debug_iframe_source.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("💾 Saved iframe HTML to debug_iframe_source.html")
        
        # Look for calendar elements
        print("\n🔍 Searching for calendar elements in iframe...")
        
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
            '[class*="date"]',
            'td',
            'div[class*="day"]',
            'span[class*="day"]'
        ]
        
        for selector in calendar_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"✅ Found {len(elements)} elements with selector: {selector}")
                for i, elem in enumerate(elements[:5]):  # Show first 5
                    print(f"   {i+1}. {elem.name} - Classes: {elem.get('class', [])}")
                    text = elem.get_text(strip=True)
                    if text:
                        print(f"      Text: {text[:50]}...")
            else:
                print(f"❌ No elements found with selector: {selector}")
        
        # Look for any elements with numbers (potential dates)
        print("\n🔍 Searching for date-like elements...")
        all_elements = soup.find_all(['div', 'span', 'td', 'li', 'button'])
        date_elements = []
        
        for elem in all_elements:
            text = elem.get_text(strip=True)
            if text.isdigit() and 1 <= int(text) <= 31:
                classes = elem.get('class', [])
                date_elements.append((text, classes, elem.name))
        
        if date_elements:
            print(f"✅ Found {len(date_elements)} potential date elements:")
            for text, classes, tag in date_elements[:15]:  # Show first 15
                print(f"   {tag} with text '{text}' - Classes: {classes}")
        else:
            print("❌ No date-like elements found")
        
        # Look for JavaScript data
        print("\n🔍 Searching for JavaScript calendar data...")
        scripts = soup.find_all('script')
        for i, script in enumerate(scripts):
            if script.string and any(keyword in script.string.lower() for keyword in ['calendar', 'date', 'availability', 'ticket', 'data']):
                print(f"📜 Script {i+1} contains data:")
                print(f"   Length: {len(script.string)} characters")
                print(f"   Preview: {script.string[:300]}...")
        
        print("\n🎯 Iframe debug complete! Check debug_iframe_source.html for full structure.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    debug_iframe()
