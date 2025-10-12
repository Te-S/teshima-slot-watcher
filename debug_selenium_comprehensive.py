#!/usr/bin/env python3
"""
Comprehensive Selenium debug script for Teshima Art Museum calendar
"""

import os
import sys
import time
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def debug_selenium():
    """Debug Selenium execution step by step"""
    print("🔍 Comprehensive Selenium Debug")
    print("=" * 50)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        print("✅ Selenium imports successful")
        
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        print("✅ Chrome options configured")
        
        # Initialize the driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✅ Chrome driver initialized")
        
        try:
            # Navigate to the iframe URL
            iframe_url = "https://web.admin-benesse-artsite.com/calendar/5?language=jpn"
            print(f"🌐 Navigating to: {iframe_url}")
            
            driver.get(iframe_url)
            print("✅ Page loaded")
            
            # Wait for basic page load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("✅ Body element found")
            
            # Wait for JavaScript to load
            print("⏳ Waiting for JavaScript to load...")
            time.sleep(10)
            
            # Get page source and save it
            page_source = driver.page_source
            with open('selenium_page_source.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            print(f"💾 Saved page source ({len(page_source)} characters)")
            
            # Check what elements are actually present
            print("\n🔍 Analyzing page structure...")
            
            # Get all elements
            all_elements = driver.find_elements(By.XPATH, "//*")
            print(f"📊 Total elements found: {len(all_elements)}")
            
            # Check for common calendar elements
            element_types = {}
            for elem in all_elements:
                tag = elem.tag_name
                element_types[tag] = element_types.get(tag, 0) + 1
            
            print("📋 Element types found:")
            for tag, count in sorted(element_types.items()):
                print(f"   {tag}: {count}")
            
            # Look for elements with text content
            text_elements = []
            for elem in all_elements:
                try:
                    text = elem.text.strip()
                    if text and len(text) < 10:  # Short text that might be dates
                        text_elements.append((elem.tag_name, text, elem.get_attribute('class')))
                except:
                    continue
            
            print(f"\n📝 Elements with text content: {len(text_elements)}")
            for tag, text, classes in text_elements[:20]:  # Show first 20
                print(f"   {tag}: '{text}' (classes: {classes})")
            
            # Look for clickable elements (potential calendar days)
            clickable_elements = driver.find_elements(By.XPATH, "//*[@onclick or @role='button' or contains(@class, 'click') or contains(@class, 'day')]")
            print(f"\n🖱️ Clickable elements: {len(clickable_elements)}")
            for i, elem in enumerate(clickable_elements[:10]):
                try:
                    text = elem.text.strip()
                    classes = elem.get_attribute('class')
                    print(f"   {i+1}. {elem.tag_name}: '{text}' (classes: {classes})")
                except:
                    print(f"   {i+1}. {elem.tag_name}: (error getting details)")
            
            # Check for any elements with numbers 1-31 (potential dates)
            date_elements = []
            for elem in all_elements:
                try:
                    text = elem.text.strip()
                    if text.isdigit() and 1 <= int(text) <= 31:
                        classes = elem.get_attribute('class')
                        date_elements.append((text, classes, elem.tag_name))
                except:
                    continue
            
            print(f"\n📅 Potential date elements: {len(date_elements)}")
            for text, classes, tag in date_elements:
                print(f"   {tag}: '{text}' (classes: {classes})")
            
            # Check for any calendar-related classes
            calendar_classes = set()
            for elem in all_elements:
                try:
                    classes = elem.get_attribute('class')
                    if classes and any(keyword in classes.lower() for keyword in ['calendar', 'day', 'date', 'month', 'year']):
                        calendar_classes.add(classes)
                except:
                    continue
            
            print(f"\n🗓️ Calendar-related classes found: {len(calendar_classes)}")
            for classes in sorted(calendar_classes):
                print(f"   {classes}")
            
            # Try to find any table or grid structure
            tables = driver.find_elements(By.TAG_NAME, "table")
            print(f"\n📊 Tables found: {len(tables)}")
            for i, table in enumerate(tables):
                try:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    cells = table.find_elements(By.TAG_NAME, "td")
                    print(f"   Table {i+1}: {len(rows)} rows, {len(cells)} cells")
                except:
                    print(f"   Table {i+1}: (error analyzing)")
            
            # Check if there are any error messages or loading indicators
            error_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'error') or contains(text(), 'Error') or contains(text(), 'loading') or contains(text(), 'Loading')]")
            if error_elements:
                print(f"\n⚠️ Error/loading elements found: {len(error_elements)}")
                for elem in error_elements:
                    print(f"   {elem.text}")
            
            print("\n🎯 Debug complete! Check selenium_page_source.html for full HTML structure.")
            
        finally:
            driver.quit()
            print("✅ Driver closed")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Install selenium: pip install selenium webdriver-manager")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_selenium()
