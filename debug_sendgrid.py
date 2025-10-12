#!/usr/bin/env python3
"""
Debug script for SendGrid integration issues
"""

import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_sendgrid():
    """Test SendGrid API directly"""
    print("🔍 SendGrid Debug Test")
    print("=" * 40)
    
    # Check environment variables
    api_key = os.getenv('SENDGRID_API_KEY')
    target_email = os.getenv('TARGET_EMAIL')
    
    print(f"📧 Target email: {target_email}")
    print(f"🔑 API key present: {'Yes' if api_key else 'No'}")
    if api_key:
        print(f"🔑 API key length: {len(api_key)} characters")
        print(f"🔑 API key starts with: {api_key[:10]}...")
    
    if not api_key:
        print("❌ SENDGRID_API_KEY not found!")
        return False
    
    if not target_email:
        print("❌ TARGET_EMAIL not found!")
        return False
    
    try:
        # Test SendGrid API connection
        print("\n🧪 Testing SendGrid API connection...")
        sg = SendGridAPIClient(api_key=api_key)
        
        # Create a simple test email
        message = Mail(
            from_email='notification@starcape.online',  # Use verified sender email
            to_emails=target_email,
            subject='🧪 SendGrid Test - Debug',
            html_content='<h2>SendGrid Test</h2><p>If you receive this email, SendGrid is working correctly!</p>'
        )
        
        print("📤 Sending test email...")
        response = sg.send(message)
        
        print(f"✅ Email sent successfully!")
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response headers: {dict(response.headers)}")
        
        return True
        
    except Exception as e:
        print(f"❌ SendGrid test failed: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_sendgrid()
    sys.exit(0 if success else 1)
