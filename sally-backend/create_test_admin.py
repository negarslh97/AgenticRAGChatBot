#!/usr/bin/env python3
"""
Create a test admin user
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.infrastructure.database_refactored import init_db
from app.domain.entities_refactored import Admin, Role
from app.core.security import get_password_hash

async def create_test_admin():
    """Create a test admin user."""
    print("👤 Creating test admin...")

    try:
        await init_db()

        # Find SuperAdmin role
        super_admin_role = await Role.find_one(Role.name == "SuperAdmin")
        if not super_admin_role:
            print("❌ SuperAdmin role not found")
            return

        # Check if test admin already exists
        existing_admin = await Admin.find_one(Admin.email == "testadmin@sally.com")
        if existing_admin:
            print("✅ Test admin already exists")
            return

        # Create test admin
        test_admin = Admin(
            email="testadmin@sally.com",
            hashed_password=get_password_hash("test123"),
            full_name="Test Admin",
            role_id=str(super_admin_role.id),
            role_name=super_admin_role.name
        )

        await test_admin.insert()
        print("✅ Test admin created successfully!")
        print("   Email: testadmin@sally.com")
        print("   Password: test123")

    except Exception as e:
        print(f"❌ Failed to create test admin: {e}")

if __name__ == "__main__":
    asyncio.run(create_test_admin())
