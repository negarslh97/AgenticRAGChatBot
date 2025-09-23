#!/usr/bin/env python3
"""
Simple test script to check if the API validation errors are fixed.
"""

import requests
import sys
import os
import asyncio

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sally-backend'))

from app.core.security import create_access_token

async def get_valid_token():
    """Create a valid admin token for testing."""
    # Create token for admin user
    token_data = {"sub": "68c5745567e64b1fa0f99b65", "type": "admin"}
    token = create_access_token(token_data)
    return token

def test_articles_endpoint():
    """Test the articles endpoint to see if validation errors are fixed."""
    try:
        # First try without auth to see if endpoint accepts unauthenticated requests
        response_no_auth = requests.get("http://127.0.0.1:8000/admin/kb/articles")
        if response_no_auth.status_code == 401:
            print("✅ Endpoint requires authentication")
        else:
            print(f"⚠️  Endpoint returned {response_no_auth.status_code} without auth")

        # Get valid token
        token = asyncio.run(get_valid_token())
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get("http://127.0.0.1:8000/admin/kb/articles", headers=headers)
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")

        if response.status_code == 200:
            print("✅ API is working correctly!")
            return True
        elif response.status_code == 401:
            print("❌ API authentication failed (token invalid)")
            return False
        elif response.status_code == 500:
            print("❌ API still has validation errors")
            return False
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error connecting to API: {e}")
        return False

if __name__ == "__main__":
    print("Testing API validation fixes...")
    success = test_articles_endpoint()
    sys.exit(0 if success else 1)
