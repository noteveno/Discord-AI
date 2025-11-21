"""
Simple Puter Test - Minimal Example
"""

from putergenai import PuterClient
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("🧪 SIMPLE PUTER TEST")
print("=" * 60)

username = os.getenv('PUTER_USERNAME')
password = os.getenv('PUTER_PASSWORD')

if not username or not password:
    print("❌ Missing credentials in .env")
    exit(1)

print(f"\n🔑 User: {username}")
print("-" * 60)

# Initialize and login
try:
    client = PuterClient()
    token = client.login(username, password)
    print(f"✅ Login successful!")
    print(f"🎟️  Token: {token[:30]}...")
except Exception as e:
    print(f"❌ Login failed: {e}")
    exit(1)

print("-" * 60)

# Simple test - use prompt instead of messages
print("\n📡 Sending simple prompt...")
try:
    response = client.ai_chat(
        prompt="Say hello in 3 words",
        test_mode=True  # Use test mode to avoid credits
    )
    
    print(f"✅ Response received!")
    print(f"   Response: {response}")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
