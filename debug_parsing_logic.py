#!/usr/bin/env python3
"""
Debug script to test the exact parsing logic step by step
"""

import os
import sys
import time
import logging
from datetime import datetime, date, timezone, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# JST timezone (UTC+9)
JST = timezone(timedelta(hours=9))

def debug_parsing_logic():
    """Debug the exact parsing logic that's failing"""
    print("🔍 Debugging Parsing Logic Step by Step")
    print("=" * 50)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        # Set up Chrome options
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
            # Navigate to the iframe URL
            iframe_url = "https://web.admin-benesse-artsite.com/calendar/5?language=jpn"
            print(f"🌐 Navigating to: {iframe_url}")
            
            driver.get(iframe_url)
            
            # Wait for JavaScript to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(10)
            
            print("✅ Page loaded, starting parsing simulation...")
            
            # Simulate the exact parsing logic from slot_watcher.py
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
                    print(f"✅ Found {len(elements)} calendar elements with selector: {selector}")
                    break
            
            if not calendar_elements:
                print("❌ No calendar elements found!")
                return
            
            print(f"\n🔍 Processing {len(calendar_elements)} calendar elements...")
            
            availability_data = {}
            processed_dates = []
            
            for i, element in enumerate(calendar_elements):
                try:
                    # Get day text
                    day_text = element.text.strip()
                    print(f"\n--- Element {i+1}: '{day_text}' ---")
                    
                    if not day_text.isdigit():
                        print(f"   ❌ Not a digit, skipping")
                        continue
                    
                    day_num = int(day_text)
                    print(f"   📅 Day number: {day_num}")
                    
                    # Check for availability status with multiple approaches
                    status = 'unknown'
                    
                    # Method 1: Check CSS classes on the element itself
                    element_classes = element.get_attribute('class') or ''
                    print(f"   🏷️ Element classes: {element_classes}")
                    
                    if 'aval' in element_classes or 'available' in element_classes:
                        status = 'available'
                        print(f"   ✅ Method 1: Found 'available' in element classes")
                    elif 'one-left' in element_classes or 'few' in element_classes:
                        status = 'few_left'
                        print(f"   ✅ Method 1: Found 'few_left' in element classes")
                    elif 'sold-out' in element_classes or 'sold' in element_classes:
                        status = 'sold_out'
                        print(f"   ✅ Method 1: Found 'sold_out' in element classes")
                    elif 'closed' in element_classes:
                        status = 'closed'
                        print(f"   ✅ Method 1: Found 'closed' in element classes")
                    
                    # Method 2: Check for child elements with price-day classes
                    if status == 'unknown':
                        print(f"   🔍 Method 2: Checking child price-day elements...")
                        try:
                            price_elements = element.find_elements(By.CSS_SELECTOR, ".price-day")
                            print(f"   📊 Found {len(price_elements)} child price-day elements")
                            
                            for j, price_elem in enumerate(price_elements):
                                price_classes = price_elem.get_attribute('class') or ''
                                print(f"   🏷️ Price element {j+1} classes: {price_classes}")
                                
                                if 'one-left' in price_classes:
                                    status = 'few_left'
                                    print(f"   ✅ Method 2: Found 'one-left' in child price classes")
                                    break
                                elif 'aval' in price_classes or 'available' in price_classes:
                                    status = 'available'
                                    print(f"   ✅ Method 2: Found 'available' in child price classes")
                                    break
                                elif 'sold-out' in price_classes:
                                    status = 'sold_out'
                                    print(f"   ✅ Method 2: Found 'sold-out' in child price classes")
                                    break
                                elif 'closed' in price_classes:
                                    status = 'closed'
                                    print(f"   ✅ Method 2: Found 'closed' in child price classes")
                                    break
                        except Exception as e:
                            print(f"   ❌ Method 2 error: {e}")
                    
                    # Method 3: Check for child elements with status classes
                    if status == 'unknown':
                        print(f"   🔍 Method 3: Checking child elements...")
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
                                    print(f"   ✅ Method 3: Found 'available' child element")
                                    break
                                elif 'one-left' in status_selector:
                                    status = 'few_left'
                                    print(f"   ✅ Method 3: Found 'one-left' child element")
                                    break
                                elif 'sold-out' in status_selector:
                                    status = 'sold_out'
                                    print(f"   ✅ Method 3: Found 'sold-out' child element")
                                    break
                                elif 'closed' in status_selector:
                                    status = 'closed'
                                    print(f"   ✅ Method 3: Found 'closed' child element")
                                    break
                    
                    print(f"   🎯 Final status: {status}")
                    
                    # Try to determine the month/year (simplified for debug)
                    year, month = 2025, 10  # From debug output
                    potential_date = date(year, month, day_num)
                    
                    # Include all dates found in the calendar
                    availability_data[potential_date.strftime('%Y-%m-%d')] = status
                    processed_dates.append((day_num, status))
                    print(f"   ✅ Added {potential_date}: {status}")
                    
                except Exception as e:
                    print(f"   ❌ Error processing element: {e}")
                    continue
            
            print(f"\n📊 Final Results:")
            print(f"   Total dates processed: {len(processed_dates)}")
            print(f"   Available dates: {len([d for d in processed_dates if d[1] == 'available'])}")
            print(f"   Few left dates: {len([d for d in processed_dates if d[1] == 'few_left'])}")
            print(f"   Sold out dates: {len([d for d in processed_dates if d[1] == 'sold_out'])}")
            print(f"   Closed dates: {len([d for d in processed_dates if d[1] == 'closed'])}")
            
            print(f"\n📅 All processed dates:")
            for day_num, status in sorted(processed_dates):
                print(f"   October {day_num}: {status}")
            
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_parsing_logic()
