"""
Test script for Playwright Service
"""
import asyncio
from app.services.playwright_service import playwright_service

async def test_create_admin():
    """Test the Playwright service admin creation"""
    print("🧪 Testing Playwright Service...")
    
    result = await playwright_service.create_admin(
        admin_email="test_admin@sally.com",
        admin_password="test123",
        admin_full_name="Test Admin",
        admin_role="Admin",
        login_email="xtra_admin@sally.com",
        login_password="123456",
        url="http://localhost:3000/super-admin"
    )
    
    if result.success:
        print(f"✅ Success: {result.result}")
    else:
        print(f"❌ Error: {result.error}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_create_admin())