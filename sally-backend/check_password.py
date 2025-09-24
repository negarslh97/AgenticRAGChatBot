#!/usr/bin/env python3
"""
Check user password hash
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.infrastructure.database_refactored import init_db
from app.domain.entities_refactored import Admin
from app.core.security import verify_password, get_password_hash

async def check_password():
    """Check user password."""
    try:
        print("🔍 Checking user passwords...")
        await init_db()
        print("✅ Database connection successful")

        # Check admins
        admins = await Admin.find_all().to_list()

        for admin in admins:
            print(f"\n👤 Admin: {admin.email}")
            print(f"  Name: {admin.full_name}")
            print(f"  Hashed Password: {admin.hashed_password}")

            # Test different passwords
            passwords_to_test = ["admin123", "admin", "password", "123456"]

            for password in passwords_to_test:
                is_valid = verify_password(password, admin.hashed_password)
                print(f"  Password '{password}': {'✅ VALID' if is_valid else '❌ INVALID'}")

            # Check if we can get the role
            try:
                role = await admin.get_role()
                print(f"  Role: {role.name if role else 'No Role'}")
            except Exception as e:
                print(f"  Role Error: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_password())
