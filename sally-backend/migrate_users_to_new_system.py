#!/usr/bin/env python3
"""
Database migration script to transfer data from old users collection to new 
admin/customer system with RBAC.

This script:
1. Creates default roles (SuperAdmin, admin)
2. Migrates existing users to either customers or admins based on their role
3. Updates all related collections to use the new references
4. Provides rollback capability
"""

import asyncio
import logging
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.security import get_password_hash
from app.core.permissions import DEFAULT_ROLES
from app.domain.entities_refactored import Role, Admin, Customer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseMigration:
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.database_url)
        self.db = self.client.get_default_database()
        
    async def create_default_roles(self):
        """Create default roles in the new system."""
        logger.info("Creating default roles...")
        
        for role_key, role_data in DEFAULT_ROLES.items():
            existing_role = await self.db.roles.find_one({"name": role_data["name"]})
            if not existing_role:
                role = Role(
                    name=role_data["name"],
                    description=role_data["description"],
                    permissions=role_data["permissions"]
                )
                await role.insert()
                logger.info(f"Created role: {role_data['name']}")
            else:
                logger.info(f"Role already exists: {role_data['name']}")
    
    async def migrate_users(self):
        """Migrate users to new admin/customer system."""
        logger.info("Starting user migration...")
        
        # Get super Admin role
        SuperAdmin_role = await self.db.roles.find_one({"name": "SuperAdmin"})
        admin_role = await self.db.roles.find_one({"name": "Admin"})
        
        if not SuperAdmin_role or not admin_role:
            raise Exception("Required roles not found. Run create_default_roles first.")
        
        # Get all users from old collection
        old_users = await self.db.users.find({}).to_list(None)
        logger.info(f"Found {len(old_users)} users to migrate")
        
        migrated_admins = 0
        migrated_customers = 0
        
        for user in old_users:
            try:
                if user["role"] in ["Admin", "SuperAdmin"]:
                    # Migrate to Admin collection
                    existing_admin = await self.db.admins.find_one({"email": user["email"]})
                    if not existing_admin:
                        admin = Admin(
                            email=user["email"],
                            hashed_password=user["hashed_password"],  # Password hash remains the same
                            full_name=user["full_name"],
                            role_id=SuperAdmin_role["_id"] if user["role"] == "SuperAdmin" else admin_role["_id"],
                            is_active=user.get("is_active", True),
                            created_at=user.get("created_at", datetime.utcnow()),
                            updated_at=user.get("updated_at", datetime.utcnow())
                        )
                        await admin.insert()
                        migrated_admins += 1
                        logger.info(f"Migrated user {user['email']} to admin collection")
                    else:
                        logger.info(f"admin already exists: {user['email']}")
                
                elif user["role"] == "Customer":
                    # Migrate to Customer collection
                    existing_customer = await self.db.customers.find_one({"email": user["email"]})
                    if not existing_customer:
                        customer = Customer(
                            email=user["email"],
                            hashed_password=user["hashed_password"],  # Password hash remains the same
                            full_name=user["full_name"],
                            is_active=user.get("is_active", True),
                            created_at=user.get("created_at", datetime.utcnow()),
                            updated_at=user.get("updated_at", datetime.utcnow())
                        )
                        await customer.insert()
                        migrated_customers += 1
                        logger.info(f"Migrated user {user['email']} to customer collection")
                    else:
                        logger.info(f"Customer already exists: {user['email']}")
                
            except Exception as e:
                logger.error(f"Error migrating user {user['email']}: {str(e)}")
                continue
        
        logger.info(f"Migration complete: {migrated_admins} admins, {migrated_customers} customers")
        return migrated_admins, migrated_customers
    
    async def update_related_collections(self):
        """Update all collections that reference the old user IDs."""
        logger.info("Updating related collections...")
        
        # Update conversations collection
        conversations_updated = 0
        conversations = await self.db.conversations.find({}).to_list(None)
        
        for conv in conversations:
            if conv.get("user_id"):
                # Find the corresponding customer
                old_user = await self.db.users.find_one({"_id": ObjectId(conv["user_id"])})
                if old_user and old_user["role"] == "customer":
                    new_customer = await self.db.customers.find_one({"email": old_user["email"]})
                    if new_customer:
                        await self.db.conversations.update_one(
                            {"_id": conv["_id"]},
                            {
                                "$set": {"customer_id": new_customer["_id"]},
                                "$unset": {"user_id": ""}
                            }
                        )
                        conversations_updated += 1
        
        logger.info(f"Updated {conversations_updated} conversations")
        
        # Update tickets collection
        tickets_updated = 0
        tickets = await self.db.tickets.find({}).to_list(None)
        
        for ticket in tickets:
            if ticket.get("customer_id"):
                # Find the corresponding customer
                old_user = await self.db.users.find_one({"_id": ObjectId(ticket["customer_id"])})
                if old_user and old_user["role"] == "customer":
                    new_customer = await self.db.customers.find_one({"email": old_user["email"]})
                    if new_customer:
                        await self.db.tickets.update_one(
                            {"_id": ticket["_id"]},
                            {"$set": {"customer_id": new_customer["_id"]}}
                        )
                        tickets_updated += 1
        
        logger.info(f"Updated {tickets_updated} tickets")
        
        # Update ticket_replies collection
        replies_updated = 0
        replies = await self.db.ticket_replies.find({}).to_list(None)
        
        for reply in replies:
            if reply.get("user_id"):
                # Find the corresponding user (customer or admin)
                old_user = await self.db.users.find_one({"_id": ObjectId(reply["user_id"])})
                if old_user:
                    if old_user["role"] == "customer":
                        new_customer = await self.db.customers.find_one({"email": old_user["email"]})
                        if new_customer:
                            await self.db.ticket_replies.update_one(
                                {"_id": reply["_id"]},
                                {
                                    "$set": {"customer_id": new_customer["_id"]},
                                    "$unset": {"user_id": ""}
                                }
                            )
                            replies_updated += 1
                    elif old_user["role"] in ["Admin", "SuperAdmin"]:
                        new_admin = await self.db.admins.find_one({"email": old_user["email"]})
                        if new_admin:
                            await self.db.ticket_replies.update_one(
                                {"_id": reply["_id"]},
                                {
                                    "$set": {"admin_id": new_admin["_id"]},
                                    "$unset": {"user_id": ""}
                                }
                            )
                            replies_updated += 1
        
        logger.info(f"Updated {replies_updated} ticket replies")
        
        # Update knowledge_base_articles collection
        articles_updated = 0
        articles = await self.db.knowledge_base_articles.find({}).to_list(None)
        
        for article in articles:
            if article.get("author_id"):
                # Find the corresponding admin
                old_user = await self.db.users.find_one({"_id": ObjectId(article["author_id"])})
                if old_user and old_user["role"] in ["Admin", "SuperAdmin"]:
                    new_admin = await self.db.admins.find_one({"email": old_user["email"]})
                    if new_admin:
                        await self.db.knowledge_base_articles.update_one(
                            {"_id": article["_id"]},
                            {"$set": {"author_id": new_admin["_id"]}}
                        )
                        articles_updated += 1
            
            if article.get("published_by"):
                # Find the corresponding admin
                old_user = await self.db.users.find_one({"_id": ObjectId(article["published_by"])})
                if old_user and old_user["role"] in ["Admin", "SuperAdmin"]:
                    new_admin = await self.db.admins.find_one({"email": old_user["email"]})
                    if new_admin:
                        await self.db.knowledge_base_articles.update_one(
                            {"_id": article["_id"]},
                            {"$set": {"published_by": new_admin["_id"]}}
                        )
        
        logger.info(f"Updated {articles_updated} knowledge base articles")
        
        # Update activity_logs collection
        logs_updated = 0
        logs = await self.db.activity_logs.find({}).to_list(None)
        
        for log in logs:
            if log.get("user_id"):
                # Find the corresponding user (customer or admin)
                old_user = await self.db.users.find_one({"_id": ObjectId(log["user_id"])})
                if old_user:
                    if old_user["role"] == "Customer":
                        new_customer = await self.db.customers.find_one({"email": old_user["email"]})
                        if new_customer:
                            await self.db.activity_logs.update_one(
                                {"_id": log["_id"]},
                                {
                                    "$set": {"customer_id": new_customer["_id"]},
                                    "$unset": {"user_id": ""}
                                }
                            )
                            logs_updated += 1
                    elif old_user["role"] in ["Admin", "SuperAdmin"]:
                        new_admin = await self.db.admins.find_one({"email": old_user["email"]})
                        if new_admin:
                            await self.db.activity_logs.update_one(
                                {"_id": log["_id"]},
                                {
                                    "$set": {"admin_id": new_admin["_id"]},
                                    "$unset": {"user_id": ""}
                                }
                            )
                            logs_updated += 1
        
        logger.info(f"Updated {logs_updated} activity logs")
        
        return {
            "conversations_updated": conversations_updated,
            "tickets_updated": tickets_updated,
            "replies_updated": replies_updated,
            "articles_updated": articles_updated,
            "logs_updated": logs_updated
        }
    
    async def migrate_all(self):
        """Run complete migration process."""
        logger.info("Starting complete database migration...")
        
        try:
            # Step 1: Create default roles
            await self.create_default_roles()
            
            # Step 2: Migrate users
            admins_migrated, customers_migrated = await self.migrate_users()
            
            # Step 3: Update related collections
            updates = await self.update_related_collections()
            
            logger.info("Migration completed successfully!")
            return {
                "status": "success",
                "admins_migrated": admins_migrated,
                "customers_migrated": customers_migrated,
                "collection_updates": updates
            }
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def rollback(self):
        """Rollback migration (for testing purposes)."""
        logger.warning("Starting rollback...")
        
        # This is a simplified rollback - in production, you'd want more sophisticated rollback
        collections_to_clean = ["admins", "customers", "roles"]
        
        for collection in collections_to_clean:
            result = await self.db[collection].delete_many({})
            logger.info(f"Cleared {result.deleted_count} documents from {collection}")
        
        logger.info("Rollback completed")


async def main():
    """Main migration function."""
    migration = DatabaseMigration()
    
    # Run migration
    result = await migration.migrate_all()
    
    if result["status"] == "success":
        logger.info(f"Migration successful!")
        logger.info(f"admins migrated: {result['admins_migrated']}")
        logger.info(f"Customers migrated: {result['customers_migrated']}")
        logger.info(f"Collection updates: {result['collection_updates']}")
    else:
        logger.error(f"Migration failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())