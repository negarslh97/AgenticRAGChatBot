#!/usr/bin/env python3
"""
Test API endpoints for knowledge base
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Authentication token
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OGM1NzQ1NTY3ZTY0YjFmYTBmOTliNjUiLCJ0eXBlIjoiU3VwZXJBZG1pbiIsImV4cCI6MTc2MTI5MjQzMX0.UVVU_clsU7uw8oFJBKkH_-cPW6maIrm6dNXFDTP_uX4"

def test_categories():
    """Test categories API endpoint."""
    print("🔍 Testing categories endpoint...")
    try:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/kb/categories", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            categories = response.json()
            print(f"✅ Found {len(categories)} categories:")
            for cat in categories:
                print(f"  - {cat['name']} (ID: {cat['id'][:8]}...)")
            return categories
        else:
            print(f"❌ Error: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return []

def test_articles():
    """Test articles API endpoint."""
    print("\n📝 Testing articles endpoint...")
    try:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        response = requests.get(f"{BASE_URL}/admin/kb/articles", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            articles = response.json()
            if isinstance(articles, list):
                print(f"✅ Found {len(articles)} articles:")
                for article in articles:
                    print(f"  - {article['title']} (ID: {article['id'][:8]}...)")
                return articles
            elif isinstance(articles, dict) and 'data' in articles:
                print(f"✅ Found {len(articles['data'])} articles:")
                for article in articles['data']:
                    print(f"  - {article['title']} (ID: {article['id'][:8]}...)")
                return articles['data']
            else:
                print(f"❌ Unexpected response format: {articles}")
                return []
        else:
            print(f"❌ Error: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return []

def test_upload_article():
    """Test creating a new article."""
    print("\n📝 Testing create article endpoint...")

    # First get a category ID
    categories = test_categories()
    if not categories:
        print("❌ No categories available for testing")
        return

    category_id = categories[0]['id']
    print(f"Using category: {categories[0]['name']} (ID: {category_id})")

    # Create test article data
    article_data = {
        "title": "Test Article Created by API Test",
        "content_markdown": "# Test Article\n\nThis is a test article created by the API test script.",
        "summary": "This is a test summary",
        "category_id": category_id,
        "tag_names": ["test", "api"],
        "status": "draft"
    }

    try:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        response = requests.post(f"{BASE_URL}/admin/kb/articles", json=article_data, headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            article = response.json()
            print("✅ Article created successfully:")
            print(f"  - Title: {article['title']}")
            print(f"  - ID: {article['id']}")
            print(f"  - Status: {article['status']}")
            return article
        else:
            print(f"❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def test_sync_status():
    """Test sync status endpoint."""
    print("\n🔄 Testing sync status endpoint...")
    try:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        response = requests.get(f"{BASE_URL}/admin/kb/sync/status", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            status = response.json()
            print("✅ Sync status:")
            print(f"  - Status: {status.get('status')}")
            print(f"  - Last sync: {status.get('last_sync')}")
            print(f"  - Pending operations: {status.get('pending_operations')}")
            return status
        else:
            print(f"❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def main():
    """Run all tests."""
    print("🧪 Starting API tests...\n")

    # Test categories
    categories = test_categories()

    # Test articles
    articles = test_articles()

    # Test creating article
    new_article = test_upload_article()

    # Test sync status
    sync_status = test_sync_status()

    print("\n📊 Summary:")
    print(f"- Categories: {len(categories)}")
    print(f"- Articles: {len(articles)}")
    print(f"- New article created: {'✅' if new_article else '❌'}")
    print(f"- Sync status available: {'✅' if sync_status else '❌'}")

if __name__ == "__main__":
    main()
