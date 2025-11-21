"""
Puter AI Direct API Test (No SDK Required)
Works with Python 3.9+
"""

import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("🧪 PUTER AI DIRECT API TEST (Python 3.9+)")
print("=" * 60)

# Get credentials
username = os.getenv('PUTER_USERNAME')
password = os.getenv('PUTER_PASSWORD')

if not username or not password:
    print("❌ PUTER_USERNAME or PUTER_PASSWORD not found in .env!")
    print("\n📝 Add to your .env file:")
    print("PUTER_USERNAME=your_username")
    print("PUTER_PASSWORD=your_password")
    exit(1)

print(f"\n🔑 Testing with user: {username}")
print("-" * 60)

# Puter API endpoints
BASE_URL = "https://api.puter.com"
LOGIN_URL = f"{BASE_URL}/login"
CHAT_URL = f"{BASE_URL}/drivers/call"

# Test 1: Login
print("\n📡 Test 1: Logging in...")
try:
    login_data = {
        "username": username,
        "password": password
    }
    
    response = requests.post(LOGIN_URL, json=login_data, timeout=10)
    
    if response.status_code == 200:
        auth_data = response.json()
        token = auth_data.get('token')
        print(f"✅ Login successful!")
        print(f"🎟️  Token: {token[:20]}..." if len(token) > 20 else f"🎟️  Token: {token}")
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        exit(1)
        
except Exception as e:
    print(f"❌ Login error: {e}")
    print("\n💡 Possible issues:")
    print("   1. Wrong username or password")
    print("   2. Account doesn't exist - create one at https://puter.com")
    print("   3. Network connection issue")
    exit(1)

print("-" * 60)

# Test 2: AI Chat
print("\n📡 Test 2: Sending AI chat request...")
test_prompt = "Say 'Hello from Puter!' in exactly 5 words."

try:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    chat_data = {
        "interface": "puter-chat-completion",
        "driver": "openai-completion",
        "method": "complete",
        "args": {
            "messages": [
                {"role": "user", "content": test_prompt}
            ],
            "model": "gpt-5-nano"
        }
    }
    
    print(f"   Prompt: {test_prompt}")
    print(f"   Model: gpt-5-nano")
    
    response = requests.post(CHAT_URL, headers=headers, json=chat_data, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Response received!")
        print(f"   Full response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Chat request failed: {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"❌ Chat error: {e}")

print("\n" + "=" * 60)
print("🎯 API Test Complete!")
print("=" * 60)
print(f"\n💡 Your auth token: {token}")
print("\n📝 You can save this token to .env:")
print(f"   PUTER_TOKEN={token}")
print("=" * 60)
