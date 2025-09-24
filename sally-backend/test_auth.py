#!/usr/bin/env python3
"""
Test authentication and get token
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    """Test login and get authentication token."""
    print("🔐 Testing login...")

    login_data = {
        "username": "xtra_admin@sally.com",
        "password": "admin123"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data=login_data
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            result = response.json()
            token = result.get("access_token")
            print("✅ Login successful!")
            print(f"  - Token: {token[:50]}...")
            return token
        else:
            print(f"❌ Login failed: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Login failed: {e}")
        return None

if __name__ == "__main__":
    token = test_login()
    if token:
        print(f"\n🎉 Token obtained: {token}")
    else:
        print("\n❌ Failed to get token!")
