#!/usr/bin/env python3
"""
Check user roles in the database.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.infrastructure.database_refactored import init_db
from app.domain.entities_refactored import Admin


async def check_user_roles():
    """Check all admin users and their roles."""

    await init_db()

    admins = await Admin.find_all().to_list()

    print(f"Found {len(admins)} admin users:")
    print("-" * 50)

    for admin in admins:
        try:
            role = await admin.get_role()
            role_name = role.name if role else "No role"

            print(f"👤 {admin.full_name} ({admin.email})")
            print(f"   Role ID: {admin.role_id}")
            print(f"   Role Name: {role_name}")
            print(f"   Is Active: {admin.is_active}")
            print(f"   ID: {admin.id}")
            print("-" * 30)
        except Exception as e:
            print(f"❌ Error getting role for {admin.email}: {e}")

    # Close connections
    from beanie import init_beanie
    # This is just to close the connection, not really needed


if __name__ == "__main__":
    asyncio.run(check_user_roles())
