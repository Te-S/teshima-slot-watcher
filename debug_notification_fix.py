#!/usr/bin/env python3
"""
Debug script to test the fixed notification logic
"""

import os
import sys
from slot_watcher import SlotWatcher

def test_notification_fix():
    """Test the fixed notification logic"""
    print("🔧 Testing Fixed Notification Logic")
    print("=" * 50)
    
    # Set up environment variables for testing
    if not os.getenv('SENDGRID_API_KEY'):
        print("❌ SENDGRID_API_KEY not set. Please set it as an environment variable.")
        return
    
    if not os.getenv('TARGET_EMAIL'):
        print("❌ TARGET_EMAIL not set. Please set it as an environment variable.")
        return
    
    watcher = SlotWatcher()
    
    # Simulate the bug scenario with museum-prefixed keys
    test_availability = {
        'teshima_2025-10-26': 'few_left',
        'teshima_2025-10-29': 'few_left',
        'teshima_2025-10-01': 'sold_out',
        'chichu_2025-10-26': 'sold_out'
    }
    
    print("🧪 Testing with simulated availability data:")
    for key, status in test_availability.items():
        print(f"   {key}: {status}")
    
    print("\n🔍 Testing change detection logic...")
    watcher.check_for_changes(test_availability)
    
    print("\n✅ Test completed! Check the logs above to see if notifications were triggered.")

if __name__ == "__main__":
    test_notification_fix()
