#!/usr/bin/env python3
"""
Test file upload functionality
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

# Authentication token - get a fresh one by running test_auth.py first
TOKEN = None  # Will be set after successful login

def test_file_upload():
    """Test uploading a file."""
    print("🧪 Testing file upload...")

    # Create a test file
    test_file_path = Path("test_upload.txt")
    test_content = "این یک فایل تست برای آپلود است.\nThis is a test file for upload.\n\nمحتوای نمونه برای تست عملکرد سیستم آپلود مقالات."
    test_file_path.write_text(test_content, encoding="utf-8")

    try:
        # Prepare the file for upload
        files = {
            'file': ('test_upload.txt', open(test_file_path, 'rb'), 'text/plain')
        }

        # Upload the file (no authentication required for testing)
        response = requests.post(
            f"{BASE_URL}/api/admin/upload",
            files=files
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            result = response.json()
            print("✅ File uploaded successfully!")
            print(f"  - File ID: {result.get('file_id')}")
            print(f"  - Article ID: {result.get('article_id')}")
            print(f"  - Filename: {result.get('filename')}")
            return result
        else:
            print(f"❌ Upload failed: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None
    finally:
        # Clean up test file
        if test_file_path.exists():
            test_file_path.unlink()

if __name__ == "__main__":
    result = test_file_upload()
    if result:
        print("\n🎉 Upload test passed!")
    else:
        print("\n❌ Upload test failed!")
