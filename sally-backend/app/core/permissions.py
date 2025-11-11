# permissions.py

"""
RBAC (Role-Based Access Control) system for admin and customer permissions.
This file defines permission constants, default roles, and FastAPI dependencies for authentication and authorization.
"""

import logging
from typing import List, Optional, Union
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from app.domain.entities import Admin, Customer, Role, PermissionDetail
from app.core.security import verify_token, get_user_info_from_token

logger = logging.getLogger(__name__)


async def get_optional_auth_header(request: Request) -> Optional[HTTPAuthorizationCredentials]:
    """Get authorization header if it exists and is valid, otherwise return None."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]
    if not token:
        return None

    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# --- 1. Permission Constants ---
# این بخش تمام کلیدهای دسترسی ممکن در سیستم را تعریف می‌کند.
class Permission:
    """Permission constants for RBAC system."""
    # admin management
    MANAGE_adminS = "admins.manage"
    VIEW_adminS = "admins.view"
    CREATE_adminS = "admins.create"
    DELETE_adminS = "admins.delete"
    
    # Customer management
    VIEW_CUSTOMERS = "customers.view"
    MANAGE_CUSTOMERS = "customers.manage"
    
    
    # Knowledge Base management
    MANAGE_KB_ARTICLES = "kb.articles.manage"
    VIEW_PUBLIC_KB = "kb.articles.view_public"
    PUBLISH_ARTICLES = "kb.articles.publish"
    DELETE_ARTICLES = "kb.articles.delete"
    
    CREATE_KB_ARTICLES = "kb.articles.create"
    UPDATE_KB_ARTICLES = "kb.articles.update"
    
    # System permissions
    VIEW_ACTIVITY_LOGS = "logs.activity.view"
    MANAGE_SYSTEM_SETTINGS = "settings.system.manage"


# --- 2. Role Name Constants ---
# تعریف ثابت‌های نام نقش‌ها برای جلوگیری از خطاهای تایپی
SUPER_ADMIN_ROLE_NAME = "SuperAdmin"
ADMIN_ROLE_NAME = "Admin"
CUSTOMER_ROLE_NAME = "Customer"
GUEST_ROLE_NAME = "Guest"


# --- 3. Default Role Configurations ---
# تعریف نقش‌های پیش‌فرض با نام‌گذاری استاندارد (snake_case)
DEFAULT_ROLES = {
    SUPER_ADMIN_ROLE_NAME: {
        "name": SUPER_ADMIN_ROLE_NAME,
        "description": "Super administrator with full system access",
        "permissions": [
            {"permission_key": Permission.MANAGE_adminS, "description": "Manage admin users", "resource": "admins", "action": "manage"},
            {"permission_key": Permission.VIEW_adminS, "description": "View admin users", "resource": "admins", "action": "view"},
            {"permission_key": Permission.CREATE_adminS, "description": "Create admin users", "resource": "admins", "action": "create"},
            {"permission_key": Permission.DELETE_adminS, "description": "Delete admin users", "resource": "admins", "action": "delete"},
            {"permission_key": Permission.MANAGE_CUSTOMERS, "description": "Manage customer users", "resource": "customers", "action": "manage"},
            {"permission_key": Permission.VIEW_CUSTOMERS, "description": "View customer users", "resource": "customers", "action": "view"},
            {"permission_key": Permission.MANAGE_KB_ARTICLES, "description": "Manage knowledge base articles", "resource": "kb_articles", "action": "manage"},
            {"permission_key": Permission.CREATE_KB_ARTICLES, "description": "Create knowledge base articles", "resource": "kb_articles", "action": "create"},
            {"permission_key": Permission.UPDATE_KB_ARTICLES, "description": "Update knowledge base articles", "resource": "kb_articles", "action": "update"},
            {"permission_key": Permission.PUBLISH_ARTICLES, "description": "Publish knowledge base articles", "resource": "kb_articles", "action": "publish"},
            {"permission_key": Permission.DELETE_ARTICLES, "description": "Delete knowledge base articles", "resource": "kb_articles", "action": "delete"},
            {"permission_key": Permission.VIEW_ACTIVITY_LOGS, "description": "View activity logs", "resource": "activity_logs", "action": "view"},
            {"permission_key": Permission.MANAGE_SYSTEM_SETTINGS, "description": "Manage system settings", "resource": "system_settings", "action": "manage"}
        ]
    },

    ADMIN_ROLE_NAME: {
        "name": ADMIN_ROLE_NAME,
        "description": "Administrator with limited access",
        "permissions": [
            {"permission_key": Permission.VIEW_CUSTOMERS, "description": "View customer users", "resource": "customers", "action": "view"},
            {"permission_key": Permission.CREATE_KB_ARTICLES, "description": "Create draft knowledge base articles", "resource": "kb_articles", "action": "create"},
            {"permission_key": Permission.UPDATE_KB_ARTICLES, "description": "Update knowledge base articles", "resource": "kb_articles", "action": "update"},
            {"permission_key": Permission.VIEW_ACTIVITY_LOGS, "description": "View activity logs", "resource": "activity_logs", "action": "view"}
        ]
    },

    CUSTOMER_ROLE_NAME: {
        "name": CUSTOMER_ROLE_NAME,
        "description": "Customer with access to their own data",
        "permissions": [
            {"permission_key": Permission.VIEW_PUBLIC_KB, "description": "View public knowledge base", "resource": "kb_articles", "action": "view_public"}
        ]
    },

    GUEST_ROLE_NAME: {
        "name": GUEST_ROLE_NAME,
        "description": "Unauthenticated user with access to public resources",
        "permissions": [
            {"permission_key": Permission.VIEW_PUBLIC_KB, "description": "View public knowledge base", "resource": "kb_articles", "action": "view_public"}
        ]
    }
}


# --- 3. Function to Create Default Roles ---
async def create_default_roles():
    """Create default roles in the database if they don't exist."""
    print(f"DEBUG: Attempting to create default roles: {list(DEFAULT_ROLES.keys())}")
    for role_name, role_data in DEFAULT_ROLES.items():
        existing_role = await Role.find_one(Role.name == role_name)
        if existing_role:
            print(f"DEBUG: Role '{role_name}' already exists, skipping creation")
        else:
            permission_details = [PermissionDetail(**perm) for perm in role_data["permissions"]]
            role = Role(
                name=role_data["name"],
                description=role_data["description"],
                permissions=permission_details,
                is_active=True # اطمینان از فعال بودن نقش
            )
            await role.insert()
            print(f"Created default role: {role_data['name']}")


# --- 4. admin Authentication and Authorization Dependencies ---
async def get_admin_from_token(token: str) -> Optional[Admin]:
    """Extract admin from JWT token, returns None if invalid or inactive."""
    logger.info(f"==== GET ADMIN FROM TOKEN START ====")
    logger.info(f"Token received: {token[:8]}...")
    try:
        payload = verify_token(token)
        logger.info(f"Token payload verified: {payload}")
        
        # توکن‌های ادمین باید نوع مشخصی داشته باشند تا با توکن مشتری اشتباه گرفته نشوند
        token_type = payload.get("type")
        logger.info(f"Checking token type: {token_type}")
        if token_type not in ["Admin", "SuperAdmin"]:
            logger.info(f"Token type '{token_type}' is not in ['Admin', 'SuperAdmin']")
            logger.info("==== GET ADMIN FROM TOKEN END (WRONG TYPE) ====")
            return None
            
        admin_id = payload.get("sub")
        if admin_id is None:
            logger.info("No 'sub' claim in token payload")
            logger.info("==== GET ADMIN FROM TOKEN END (NO SUB) ====")
            return None
            
        logger.info(f"Looking for admin with ID: {admin_id}")
        admin = await Admin.get(admin_id)
        
        if admin:
            logger.info(f"Admin found: {admin.full_name} ({admin.email}) - Active: {admin.is_active}")
            if admin.is_active:
                logger.info("==== GET ADMIN FROM TOKEN END (SUCCESS) ====")
            else:
                logger.info("==== GET ADMIN FROM TOKEN END (INACTIVE) ====")
        else:
            logger.info(f"No admin found with ID: {admin_id}")
            logger.info("==== GET ADMIN FROM TOKEN END (NOT FOUND) ====")
            
        return admin if admin and admin.is_active else None
        
    except Exception as e:
        logger.error(f"Error getting admin from token: {str(e)}")
        logger.info("==== GET ADMIN FROM TOKEN END (ERROR) ====")
        return None

async def get_current_admin(credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_auth_header)) -> Admin:
    """FastAPI dependency to get the current authenticated and active Admin."""
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    admin = await get_admin_from_token(credentials.credentials)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Admin authentication credentials")
    return admin


async def has_permission(admin: Admin, permission: str) -> bool:
    """Check if an admin has a specific permission."""
    try:
        role = await admin.get_role()
        if not role or not role.is_active:
            logger.warning(f"Permission check failed: Admin {admin.email} has no active role")
            return False
        
        permission_keys = {perm.permission_key for perm in role.permissions}
        has_perm = permission in permission_keys
        
        if not has_perm:
            logger.warning(f"Permission check failed: Admin {admin.email} (role: {role.name}) does not have permission '{permission}'. Available permissions: {permission_keys}")
        
        return has_perm
    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        return False

def get_current_admin_with_permission(permission: str):
    """Dependency factory for checking if the current admin has a specific permission."""
    async def dependency(admin: Admin = Depends(get_current_admin)) -> Admin:
        role = await admin.get_role()
        if not role or not role.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role not found or inactive")
        
        permission_keys = {perm.permission_key for perm in role.permissions}
        if permission not in permission_keys:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission '{permission}' required")
        
        return admin
    return dependency


# --- 5. Customer Authentication Dependencies ---
async def get_current_customer_from_token(token: str) -> Optional[Customer]:
    """Extract customer from JWT token, returns None if invalid or inactive."""
    logger.info(f"==== GET CUSTOMER FROM TOKEN START ====")
    logger.info(f"Token received: {token[:8]}...")
    try:
        payload = verify_token(token)
        logger.info(f"Token payload verified: {payload}")
        
        # توکن‌های مشتری باید نوع مشخصی داشته باشند
        if payload.get("type") != "Customer":
            logger.info(f"Token type is not 'Customer': {payload.get('type')}")
            logger.info("==== GET CUSTOMER FROM TOKEN END (WRONG TYPE) ====")
            return None
            
        customer_id = payload.get("sub")
        if customer_id is None:
            logger.info("No 'sub' claim in token payload")
            logger.info("==== GET CUSTOMER FROM TOKEN END (NO SUB) ====")
            return None
            
        logger.info(f"Looking for customer with ID: {customer_id}")
        customer = await Customer.get(customer_id)
        
        if customer:
            logger.info(f"Customer found: {customer.full_name} ({customer.email}) - Active: {customer.is_active}")
            if customer.is_active:
                logger.info("==== GET CUSTOMER FROM TOKEN END (SUCCESS) ====")
            else:
                logger.info("==== GET CUSTOMER FROM TOKEN END (INACTIVE) ====")
        else:
            logger.info(f"No customer found with ID: {customer_id}")
            logger.info("==== GET CUSTOMER FROM TOKEN END (NOT FOUND) ====")
            
        return customer if customer and customer.is_active else None
        
    except Exception as e:
        logger.error(f"Error getting customer from token: {str(e)}")
        logger.info("==== GET CUSTOMER FROM TOKEN END (ERROR) ====")
        return None

async def get_current_customer(credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_auth_header)) -> Customer:
    """FastAPI dependency to get the current authenticated and active customer."""
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    customer = await get_current_customer_from_token(credentials.credentials)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid customer authentication credentials")
    return customer


# --- 6. Optional & Combined User Dependencies ---
async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_auth_header)) -> Union[Admin, Customer]:
    """
    FastAPI dependency to get the current authenticated user (admin or customer).
    
    This function optimizes user identification by:
    1. Using unified token verification
    2. Checking user type once to prevent redundant authentication attempts
    3. Direct database lookup based on user type
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    try:
        # Use unified user info extraction to avoid redundant token verification
        user_type, payload = get_user_info_from_token(credentials.credentials)
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing user ID")
        
        logger.info(f"🔍 User type identified: {user_type}, User ID: {user_id}")
        
        # Direct database lookup based on user type
        if user_type in ["Admin", "SuperAdmin"]:
            admin = await Admin.get(user_id)
            if admin and admin.is_active:
                logger.info(f"✅ Admin authenticated: {admin.full_name} ({admin.email})")
                return admin
            else:
                logger.warning(f"⚠️ Admin not found or inactive: {user_id}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")
        
        elif user_type == "Customer":
            customer = await Customer.get(user_id)
            if customer and customer.is_active:
                logger.info(f"✅ Customer authenticated: {customer.full_name} ({customer.email})")
                return customer
            else:
                logger.warning(f"⚠️ Customer not found or inactive: {user_id}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid customer credentials")
        
        else:
            logger.error(f"❌ Unknown user type: {user_type}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Authentication error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_auth_header)) -> Optional[Union[Admin, Customer]]:
    """Gets the current user (admin or Customer) if authenticated, otherwise returns None."""
    if not credentials or not credentials.credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

async def get_optional_admin(credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_auth_header)) -> Optional[Admin]:
    """
    اگر توکن معتبر ادمین در هدر وجود داشته باشد، ادمین را برمی‌گرداند.
    در غیر این صورت، به جای ایجاد خطا، None برمی‌گرداند.
    """
    if not credentials or not credentials.credentials:
        return None
    
    # ما از try...except استفاده نمی‌کنیم چون get_admin_from_token خودش در صورت خطا None برمی‌گرداند
    return await get_admin_from_token(credentials.credentials)

async def get_optional_customer(credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_auth_header)) -> Optional[Customer]:
    """

    اگر توکن معتبر مشتری در هدر وجود داشته باشد، مشتری را برمی‌گرداند.
    در غیر این صورت، به جای ایجاد خطا، None برمی‌گرداند.
    """
    if not credentials or not credentials.credentials:
        return None
        
    return await get_current_customer_from_token(credentials.credentials)