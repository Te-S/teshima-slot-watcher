#!/usr/bin/env python3
"""
Test script for Teshima Art Museum Slot Watcher
This script sends a test email to verify SendGrid integration is working
"""

import os
import sys
from slot_watcher import SlotWatcher
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    print("🧪 Teshima Art Museum Slot Watcher - Test Mode")
    print("=" * 50)
    
    # Check if SendGrid API key is set
    if not os.getenv('SENDGRID_API_KEY'):
        print("❌ Error: SENDGRID_API_KEY environment variable not set")
        print("Please set your SendGrid API key:")
        print("export SENDGRID_API_KEY='your_api_key_here'")
        return False
    
    if not os.getenv('TARGET_EMAIL'):
        print("❌ Error: TARGET_EMAIL environment variable not set")
        print("Please set your target email:")
        print("export TARGET_EMAIL='your_email@example.com'")
        return False
    
    print(f"📧 Target email: {os.getenv('TARGET_EMAIL')}")
    print(f"🔑 SendGrid API key: {'*' * 20}{os.getenv('SENDGRID_API_KEY')[-4:]}")
    print()
    
    try:
        # Create watcher instance
        watcher = SlotWatcher()
        
        # Run in test mode
        print("🚀 Starting test run...")
        watcher.run(test_mode=True)
        
        print("✅ Test completed successfully!")
        print("📧 Check your email for the test report")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
