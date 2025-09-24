#!/usr/bin/env python3
"""
Check user information in database
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.infrastructure.database_refactored import init_db
from app.domain.entities_refactored import Admin, Role

async def check_users():
    """Check user information."""
    try:
        print("🔍 Checking user information...")
        await init_db()
        print("✅ Database connection successful")

        # Check admins
        admins = await Admin.find_all().to_list()
        print(f"\n👤 Found {len(admins)} admins:")

        for admin in admins:
            role = await admin.get_role()
            role_name = role.name if role else "No Role"

            print(f"  - Email: {admin.email}")
            print(f"    Name: {admin.full_name}")
            print(f"    Role: {role_name}")
            print(f"    Active: {admin.is_active}")
            print(f"    Role ID: {admin.role_id}")
            print()

        # Check roles
        roles = await Role.find_all().to_list()
        print(f"\n🏷️ Found {len(roles)} roles:")

        for role in roles:
            print(f"  - {role.name} (ID: {role.id})")

        print("\n💡 Try using one of the admin emails above with password 'admin123'")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_users())
