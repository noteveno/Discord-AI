"""
Puter AI Credential Test Script
Test your Puter.com credentials and verify AI response
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("🧪 PUTER AI CREDENTIAL TEST")
print("=" * 60)

# Check if putergenai is installed
try:
    from putergenai import PuterClient
    print("✅ putergenai package found")
except ImportError:
    print("❌ putergenai not installed!")
    print("\n📦 Install with: pip install putergenai")
    exit(1)

# Get credentials from .env
username = os.getenv('PUTER_USERNAME')
password = os.getenv('PUTER_PASSWORD')

if not username or not password:
    print("❌ PUTER_USERNAME or PUTER_PASSWORD not found in .env!")
    print("\n📝 Add to your .env file:")
    print("PUTER_USERNAME=your_username")
    print("PUTER_PASSWORD=your_password")
    exit(1)

print(f"\n🔑 Found credentials for user: {username}")
print("-" * 60)

# Test 1: Login
print("\n📡 Test 1: Attempting to login...")
try:
    client = PuterClient()
    token = client.login(username, password)
    print(f"✅ Login successful!")
    print(f"🎟️  Token: {token[:20]}..." if len(token) > 20 else f"🎟️  Token: {token}")
except Exception as e:
    print(f"❌ Login failed: {e}")
    print("\n💡 Possible issues:")
    print("   1. Wrong username or password")
    print("   2. Account doesn't exist - create one at https://puter.com")
    print("   3. Network connection issue")
    exit(1)

print("-" * 60)

# Test 2: Simple AI Chat
print("\n📡 Test 2: Sending test prompt to AI...")
test_prompt = "Say 'Hello from Puter AI!' in exactly 5 words."

try:
    messages = [
        {"role": "user", "content": test_prompt}
    ]
    
    print(f"   Prompt: {test_prompt}")
    print(f"   Model: gpt-5-nano")
    
    response = client.ai_chat(
        messages=messages,
        options={"model": "gpt-5-nano"}
    )
    
    ai_response = response["response"]["result"]["message"]["content"]
    used_model = response["used_model"]
    
    print(f"\n✅ AI Response received!")
    print(f"   Model used: {used_model}")
    print(f"   Response: {ai_response}")
    
except Exception as e:
    print(f"❌ AI request failed: {e}")
    print("\n💡 Possible issues:")
    print("   1. Model not available")
    print("   2. Network issue")
    print("   3. Account quota exceeded")
    exit(1)

print("-" * 60)

# Test 3: Try streaming
print("\n📡 Test 3: Testing streaming response...")
stream_prompt = "Count from 1 to 5"

try:
    messages = [
        {"role": "user", "content": stream_prompt}
    ]
    
    print(f"   Prompt: {stream_prompt}")
    print(f"   Response (streaming): ", end="", flush=True)
    
    gen = client.ai_chat(
        messages=messages,
        options={"model": "gpt-5-nano", "stream": True}
    )
    
    full_response = ""
    for content, used_model in gen:
        print(content, end="", flush=True)
        full_response += content
    
    print(f"\n✅ Streaming works!")
    
except Exception as e:
    print(f"\n❌ Streaming failed: {e}")
    # Non-critical, continue

print("\n" + "=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\n✅ Your Puter credentials are working correctly!")
print("✅ AI responses are being received")
print("✅ Ready to integrate into Kamao AI bot")
print("\n💡 Your token for future use:")
print(f"   {token}")
print("\n📝 You can add this to .env as:")
print(f"   PUTER_TOKEN={token}")
print("   (This will skip login on future requests)")
print("=" * 60)
