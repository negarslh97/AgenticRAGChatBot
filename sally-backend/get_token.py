#!/usr/bin/env python3
"""
Get authentication token for testing
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def get_token():
    """Get authentication token."""
    print("🔐 Getting authentication token...")

    login_data = {
        "username": "xtra_admin@sally.com",  # SuperAdmin email
        "password": "123456"  # Correct password
    }

    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"🔑 Token: {data['access_token'][:50]}...")
            print(f"👤 User: {data['user']['full_name']} ({data['user']['email']})")
            print(f"🔄 User Type: {data['user_type']}")

            return data['access_token']
        else:
            print(f"❌ Login failed: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

if __name__ == "__main__":
    token = get_token()
    if token:
        print("\n💡 Use this token in your test scripts:")
        print(f"TOKEN = '{token}'")
