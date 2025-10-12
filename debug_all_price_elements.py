#!/usr/bin/env python3
"""
Debug script to see ALL price-day elements for October 13th
"""

import os
import sys
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def debug_all_price_elements():
    """Debug all price elements for October 13th"""
    print("🔍 Debugging ALL Price Elements for October 13th")
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
            
            print("✅ Page loaded, finding October 13th...")
            
            # Find October 13th button
            october_13_buttons = driver.find_elements(By.XPATH, "//button[text()='13']")
            
            if not october_13_buttons:
                print("❌ October 13th button not found!")
                return
            
            october_13_button = october_13_buttons[0]
            print(f"✅ Found October 13th button")
            
            # Get the parent container
            parent = october_13_button.find_element(By.XPATH, "..")
            print(f"✅ Found parent container")
            
            # Get ALL price-day elements in the parent
            price_elements = parent.find_elements(By.CSS_SELECTOR, ".price-day")
            print(f"💰 Found {len(price_elements)} price-day elements")
            
            for i, price_elem in enumerate(price_elements):
                try:
                    classes = price_elem.get_attribute('class') or ''
                    text = price_elem.text.strip()
                    print(f"   {i+1}. '{text}' (classes: {classes})")
                    
                    # Check if this element has one-left
                    if 'one-left' in classes:
                        print(f"      🎯 FOUND ONE-LEFT! This should be few_left status")
                except Exception as e:
                    print(f"   {i+1}. Error: {e}")
            
            # Also check for any element with one-left anywhere in the parent
            one_left_elements = parent.find_elements(By.CSS_SELECTOR, "[class*='one-left']")
            print(f"\n⚠️ Elements with 'one-left' anywhere in parent ({len(one_left_elements)}):")
            for i, elem in enumerate(one_left_elements):
                try:
                    classes = elem.get_attribute('class') or ''
                    text = elem.text.strip()
                    print(f"   {i+1}. '{text}' (classes: {classes})")
                except Exception as e:
                    print(f"   {i+1}. Error: {e}")
            
            # Check the entire page for one-left elements
            all_one_left = driver.find_elements(By.CSS_SELECTOR, "[class*='one-left']")
            print(f"\n🔍 ALL elements with 'one-left' on entire page ({len(all_one_left)}):")
            for i, elem in enumerate(all_one_left):
                try:
                    classes = elem.get_attribute('class') or ''
                    text = elem.text.strip()
                    print(f"   {i+1}. '{text}' (classes: {classes})")
                except Exception as e:
                    print(f"   {i+1}. Error: {e}")
            
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_all_price_elements()
