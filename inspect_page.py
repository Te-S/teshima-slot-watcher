#!/usr/bin/env python3
"""
Test script to inspect the Teshima Art Museum booking page structure
This will help us understand how the calendar is implemented
"""

import requests
from bs4 import BeautifulSoup
import json

def inspect_page():
    url = "https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/185773"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print("Fetching page...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("=== PAGE ANALYSIS ===")
        print(f"Title: {soup.title.string if soup.title else 'No title'}")
        
        # Look for calendar-related elements
        print("\n=== CALENDAR ELEMENTS ===")
        
        # Check for common calendar patterns
        calendar_keywords = ['calendar', 'date', 'day', 'month', 'year', 'slot', 'available']
        
        for keyword in calendar_keywords:
            elements = soup.find_all(attrs={'class': lambda x: x and keyword in str(x).lower()})
            if elements:
                print(f"\nElements with '{keyword}' in class:")
                for elem in elements[:5]:  # Show first 5
                    print(f"  {elem.name}: {elem.get('class')} - {elem.get_text()[:100]}...")
        
        # Look for data attributes
        print("\n=== DATA ATTRIBUTES ===")
        data_elements = soup.find_all(attrs={'data-date': True})
        print(f"Elements with data-date: {len(data_elements)}")
        for elem in data_elements[:5]:
            print(f"  {elem.name}: data-date='{elem.get('data-date')}' class='{elem.get('class')}'")
        
        # Look for JavaScript variables that might contain calendar data
        print("\n=== JAVASCRIPT ANALYSIS ===")
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                script_content = script.string
                if any(keyword in script_content.lower() for keyword in ['calendar', 'date', 'available', 'slot']):
                    print(f"Script contains calendar-related code:")
                    print(f"  {script_content[:200]}...")
                    break
        
        # Look for forms or input elements
        print("\n=== FORMS AND INPUTS ===")
        forms = soup.find_all('form')
        print(f"Found {len(forms)} forms")
        
        inputs = soup.find_all('input')
        date_inputs = [inp for inp in inputs if inp.get('type') in ['date', 'datetime-local', 'text'] and 
                      any(keyword in str(inp.get('name', '')).lower() for keyword in ['date', 'day', 'time'])]
        print(f"Found {len(date_inputs)} date-related inputs")
        
        # Save the HTML for manual inspection
        with open('page_source.html', 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))
        print(f"\nPage source saved to 'page_source.html' for manual inspection")
        
        # Look for specific symbols or icons
        print("\n=== SYMBOL ANALYSIS ===")
        symbols = soup.find_all(['i', 'span', 'div'], class_=lambda x: x and any(
            symbol in str(x).lower() for symbol in ['circle', 'triangle', 'cross', 'available', 'sold', 'closed', 'icon']
        ))
        print(f"Found {len(symbols)} potential symbol elements")
        for symbol in symbols[:10]:
            print(f"  {symbol.name}: class='{symbol.get('class')}' text='{symbol.get_text()[:50]}'")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    inspect_page()
