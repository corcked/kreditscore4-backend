"""
Test script for Bot API endpoints
"""
import asyncio
import aiohttp
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
BOT_API_KEY = "test-bot-api-key"  # Make sure this matches your .env

async def test_bot_endpoints():
    """Test all bot API endpoints"""
    
    async with aiohttp.ClientSession() as session:
        headers = {"X-Bot-Token": BOT_API_KEY}
        
        print("🧪 Testing Bot API Endpoints\n")
        
        # Test 1: Health Check
        print("1️⃣ Testing /api/bot/health")
        try:
            async with session.get(
                f"{BASE_URL}/api/bot/health",
                headers=headers
            ) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Response: {json.dumps(data, indent=2)}")
                else:
                    print(f"   Error: {await resp.text()}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print("\n" + "-"*50 + "\n")
        
        # Test 2: Init Auth
        print("2️⃣ Testing /api/bot/auth/init")
        init_data = {
            "loan_amount": 50000,
            "loan_term": 12,
            "loan_purpose": "Test purpose",
            "monthly_income": 80000
        }
        
        auth_token = None
        try:
            async with session.post(
                f"{BASE_URL}/api/bot/auth/init",
                headers=headers,
                json=init_data
            ) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Response: {json.dumps(data, indent=2)}")
                    auth_token = data.get("auth_token")
                else:
                    print(f"   Error: {await resp.text()}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print("\n" + "-"*50 + "\n")
        
        # Test 3: Complete Auth
        if auth_token:
            print("3️⃣ Testing /api/bot/auth/complete")
            complete_data = {
                "auth_token": auth_token,
                "telegram_id": 123456789,
                "phone": "+1234567890",
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser"
            }
            
            try:
                async with session.post(
                    f"{BASE_URL}/api/bot/auth/complete",
                    headers=headers,
                    json=complete_data
                ) as resp:
                    print(f"   Status: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   Response: {json.dumps(data, indent=2)}")
                    else:
                        print(f"   Error: {await resp.text()}")
            except Exception as e:
                print(f"   Exception: {e}")
        
        print("\n" + "-"*50 + "\n")
        
        # Test 4: Get User
        print("4️⃣ Testing /api/bot/users/{telegram_id}")
        try:
            async with session.get(
                f"{BASE_URL}/api/bot/users/123456789",
                headers=headers
            ) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Response: {json.dumps(data, indent=2)}")
                else:
                    print(f"   Error: {await resp.text()}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print("\n" + "-"*50 + "\n")
        
        # Test 5: Invalid Token
        print("5️⃣ Testing with invalid bot token")
        bad_headers = {"X-Bot-Token": "invalid-token"}
        try:
            async with session.get(
                f"{BASE_URL}/api/bot/health",
                headers=bad_headers
            ) as resp:
                print(f"   Status: {resp.status}")
                print(f"   Expected: 401 Unauthorized")
                if resp.status != 401:
                    print("   ❌ Security issue: Invalid token should be rejected!")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print("\n✅ Bot API testing completed!")

if __name__ == "__main__":
    asyncio.run(test_bot_endpoints())