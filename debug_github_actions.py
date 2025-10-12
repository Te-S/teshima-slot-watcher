#!/usr/bin/env python3
"""
GitHub Actions debug script to see what's happening in the cloud environment
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

def debug_github_actions():
    """Debug what's happening in GitHub Actions environment"""
    print("🔍 GitHub Actions Environment Debug")
    print("=" * 50)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        # Set up Chrome options for GitHub Actions
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
            print(f"ChromeDriver setup failed: {e}")
            # Fallback: try without explicit path
            driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Navigate to the iframe URL
            iframe_url = "https://web.admin-benesse-artsite.com/calendar/5?language=jpn"
            print(f"🌐 Navigating to: {iframe_url}")
            
            driver.get(iframe_url)
            
            # Wait for JavaScript to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(15)  # Extra wait for GitHub Actions
            
            print("✅ Page loaded, analyzing calendar...")
            
            # Save page source for inspection
            page_source = driver.page_source
            print(f"📄 Page source length: {len(page_source)} characters")
            
            # Look for October 13th specifically
            october_13_elements = driver.find_elements(By.XPATH, "//button[contains(@class, 'item') and .//span[text()='13']]")
            print(f"🔍 Found {len(october_13_elements)} October 13th elements")
            
            if october_13_elements:
                october_13 = october_13_elements[0]
                print("✅ October 13th found!")
                
                # Check its classes
                classes = october_13.get_attribute('class')
                print(f"🏷️ October 13th classes: {classes}")
                
                # Check for child price-day elements
                price_elements = october_13.find_elements(By.CSS_SELECTOR, ".price-day")
                print(f"💰 Found {len(price_elements)} child price-day elements")
                
                for i, price_elem in enumerate(price_elements):
                    price_classes = price_elem.get_attribute('class') or ''
                    print(f"   {i+1}. Price classes: {price_classes}")
                    
                    if 'one-left' in price_classes:
                        print(f"      🎯 FOUND ONE-LEFT!")
                    elif 'sold-out' in price_classes:
                        print(f"      ❌ Found sold-out")
                    elif 'aval' in price_classes:
                        print(f"      ✅ Found available")
            else:
                print("❌ October 13th not found!")
                
                # Check what dates are actually available
                all_buttons = driver.find_elements(By.CSS_SELECTOR, "button.item")
                print(f"📅 Found {len(all_buttons)} calendar buttons")
                
                for i, button in enumerate(all_buttons[:10]):  # Show first 10
                    try:
                        text = button.text.strip()
                        classes = button.get_attribute('class')
                        print(f"   {i+1}. '{text}' (classes: {classes})")
                    except:
                        print(f"   {i+1}. Error getting button details")
            
            # Check for any one-left elements on the page
            one_left_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='one-left']")
            print(f"\n⚠️ Elements with 'one-left' on page: {len(one_left_elements)}")
            for i, elem in enumerate(one_left_elements):
                try:
                    classes = elem.get_attribute('class')
                    text = elem.text.strip()
                    print(f"   {i+1}. '{text}' (classes: {classes})")
                except:
                    print(f"   {i+1}. Error getting element details")
            
            # Check current date/time
            current_time = datetime.now(JST)
            print(f"\n🕐 Current JST time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_github_actions()
