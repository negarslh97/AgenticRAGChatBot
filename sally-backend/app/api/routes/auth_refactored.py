from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from bson import ObjectId
from typing import Union
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.domain.entities_refactored import Admin, Customer, Role, ActivityLog
from app.core.permissions import get_current_admin, get_current_customer, get_optional_auth_header
from app.core.permissions import get_admin_from_token, get_current_customer_from_token, Permission
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class CustomerRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class AdminRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role_id: str  # ObjectId as string


class CustomerResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool


class AdminResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role_id: str
    role: str
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str
    user_type: str  # "admin" or "customer"
    user: Union[CustomerResponse, AdminResponse]


class UserLoginResponse(BaseModel):
    """Response for login endpoint that can handle both admin and customer."""
    access_token: str
    token_type: str
    user_type: str
    user: Union[CustomerResponse, AdminResponse]


@router.post("/register/customer", response_model=CustomerResponse)
async def register_customer(customer_data: CustomerRegister):
    """Register a new customer user."""
    # Check if customer already exists
    existing_customer = await Customer.find_one(Customer.email == customer_data.email)
    if existing_customer:
        logger.warning(f"Registration failed: Email {customer_data.email} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new customer
    customer = Customer(
        email=customer_data.email,
        hashed_password=get_password_hash(customer_data.password),
        full_name=customer_data.full_name
    )

    await customer.insert()

    logger.info(f"✅ New customer registered: {customer.full_name} ({customer.email}) - ID: {customer.id}")

    return CustomerResponse(
        id=str(customer.id),
        email=customer.email,
        full_name=customer.full_name,
        is_active=customer.is_active
    )


@router.post("/register/admin", response_model=AdminResponse)
async def register_admin(
    admin_data: AdminRegister,
    current_admin: Admin = Depends(get_current_admin)
):
    """Register a new admin user (requires admin authentication)."""
    # Verify the current admin has permission to create admins
    current_admin_role = await current_admin.get_role()
    if not current_admin_role or Permission.MANAGE_adminS not in current_admin_role.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: cannot create admin users"
        )
    
    # Check if admin already exists
    existing_admin = await Admin.find_one(Admin.email == admin_data.email)
    if existing_admin:
        logger.warning(f"Admin registration failed: Email {admin_data.email} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Verify role exists
    try:
        role_id = ObjectId(admin_data.role_id)
        role = await Role.get(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role ID"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role ID format"
        )
    
    # Create new admin
    admin = Admin(
        email=admin_data.email,
        hashed_password=get_password_hash(admin_data.password),
        full_name=admin_data.full_name,
        role_id=role_id
    )
    
    await admin.insert()

    logger.info(f"✅ New admin registered: {admin.full_name} ({admin.email}) - Role: {role.name} - Created by: {current_admin.full_name} - ID: {admin.id}")

    # Log activity
    activity_log = ActivityLog(
        admin_id=str(current_admin.id),
        action="create_admin",
        resource_type="admin",
        resource_id=str(admin.id),
        details={"created_admin_email": admin.email, "role": role.name}
    )
    await activity_log.insert()

    return AdminResponse(
        id=str(admin.id),
        email=admin.email,
        full_name=admin.full_name,
        role_id=str(admin.role_id),
        role=role.name,
        is_active=admin.is_active
    )


@router.post("/login", response_model=UserLoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user (admin or customer) and return JWT token."""
    email = form_data.username
    
    # Try to authenticate as admin first
    admin = await Admin.find_one(Admin.email == email)
    if admin and verify_password(form_data.password, admin.hashed_password):
        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive admin account"
            )
        
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)

        # Get admin's role information
        role = await admin.get_role()
        role_name = role.name if role else "unknown"

        logger.info(f"🔐 Admin login: {admin.full_name} ({admin.email}) - Role: {role_name} - ID: {admin.id}")

        # Determine user type based on role
        user_type = "SuperAdmin" if role_name == "SuperAdmin" else "Admin"

        # Create JWT token with correct type
        access_token = create_access_token(
            data={"sub": str(admin.id), "type": user_type},
            expires_delta=access_token_expires
        )

        # Log login activity
        activity_log = ActivityLog(
            admin_id=str(admin.id),
            action="login",
            resource_type="auth",
            details={"user_type": user_type}
        )
        await activity_log.insert()

        return UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_type=user_type,
            user=AdminResponse(
                id=str(admin.id),
                email=admin.email,
                full_name=admin.full_name,
                role_id=str(admin.role_id),
                role=role_name,
                is_active=admin.is_active
            )
        )
    
    # Try to authenticate as customer
    customer = await Customer.find_one(Customer.email == email)
    if customer and verify_password(form_data.password, customer.hashed_password):
        if not customer.is_active:
            logger.warning(f"Login failed: Inactive customer account - {customer.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive customer account"
            )

        logger.info(f"🔐 Customer login: {customer.full_name} ({customer.email}) - ID: {customer.id}")

        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(customer.id), "type": "customer"},
            expires_delta=access_token_expires
        )

        return UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_type="customer",
            user=CustomerResponse(
                id=str(customer.id),
                email=customer.email,
                full_name=customer.full_name,
                is_active=customer.is_active
            )
        )
    
    # If neither admin nor customer authentication succeeded
    logger.warning(f"❌ Login failed: Invalid credentials for email {email}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _get_current_user_info(token: str):
    """Helper function to get current user information."""
    # Try to get admin first
    admin = await get_admin_from_token(token)
    if admin:
        role = await admin.get_role()
        role_name = role.name if role else "unknown"
        # Set user_type based on actual role
        user_type = "SuperAdmin" if role_name == "SuperAdmin" else "Admin"
        return {
            "user_type": user_type,
            "user": {
                "id": str(admin.id),
                "email": admin.email,
                "full_name": admin.full_name,
                "role": role_name,
                "is_active": admin.is_active
            }
        }

    # Try to get customer
    customer = await get_current_customer_from_token(token)
    if customer:
        return {
            "user_type": "customer",
            "user": {
                "id": str(customer.id),
                "email": customer.email,
                "full_name": customer.full_name,
                "role": "Customer",
                "is_active": customer.is_active
            }
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials"
    )


@router.get("/me")
async def get_current_user_info(request: Request):
    """Get current user information (admin or customer)."""
    logger.info("==== GET CURRENT USER INFO START ====")
    logger.info(f"Request headers: {dict(request.headers)}")
    
    auth_header = request.headers.get("Authorization")
    logger.info(f"Authorization header present: {bool(auth_header)}")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("Authentication failed: No Bearer token in Authorization header")
        logger.info("==== GET CURRENT USER INFO END (NO AUTH) ====")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    token = auth_header.split(" ")[1]
    logger.info(f"Token extracted: {token[:20]}...")
    
    try:
        result = await _get_current_user_info(token)
        logger.info(f"User info retrieved successfully: {result}")
        logger.info("==== GET CURRENT USER INFO END (SUCCESS) ====")
        return result
    except Exception as e:
        logger.error(f"Failed to get user info: {str(e)}")
        logger.info("==== GET CURRENT USER INFO END (ERROR) ====")
        raise


@router.get("/users/me")
async def get_current_user_info_alias(request: Request):
    """Alias for /me endpoint."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    token = auth_header.split(" ")[1]
    return await _get_current_user_info(token)


@router.post("/refresh")
async def refresh_token(request: Request):
    """Refresh access token using current valid token."""
    logger.info("==== TOKEN REFRESH START ====")
    
    auth_header = request.headers.get("Authorization")
    logger.info(f"Authorization header present: {bool(auth_header)}")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("Token refresh failed: No Bearer token in Authorization header")
        logger.info("==== TOKEN REFRESH END (NO AUTH) ====")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    token = auth_header.split(" ")[1]
    logger.info(f"Token extracted for refresh: {token[:20]}...")

    # Try to get admin first
    logger.info("Attempting to get admin from token...")
    admin = await get_admin_from_token(token)
    if admin:
        logger.info(f"Admin found for refresh: {admin.full_name} ({admin.email})")
        # Create new access token for admin
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        new_access_token = create_access_token(
            data={"sub": str(admin.id), "type": "Admin"},
            expires_delta=access_token_expires
        )

        # Get admin's role information
        role = await admin.get_role()
        role_name = role.name if role else "unknown"

        logger.info(f"🔄 Admin token refresh successful: {admin.full_name} ({admin.email}) - Role: {role_name} - ID: {admin.id}")
        logger.info("==== TOKEN REFRESH END (ADMIN SUCCESS) ====")

        return UserLoginResponse(
            access_token=new_access_token,
            token_type="bearer",
            user_type="Admin",
            user=AdminResponse(
                id=str(admin.id),
                email=admin.email,
                full_name=admin.full_name,
                role_id=str(admin.role_id),
                role=role_name,
                is_active=admin.is_active
            )
        )

    # Try to get customer
    logger.info("Admin not found, attempting to get customer from token...")
    customer = await get_current_customer_from_token(token)
    if customer:
        logger.info(f"Customer found for refresh: {customer.full_name} ({customer.email})")
        # Create new access token for customer
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        new_access_token = create_access_token(
            data={"sub": str(customer.id), "type": "customer"},
            expires_delta=access_token_expires
        )

        logger.info(f"🔄 Customer token refresh successful: {customer.full_name} ({customer.email}) - ID: {customer.id}")
        logger.info("==== TOKEN REFRESH END (CUSTOMER SUCCESS) ====")

        return UserLoginResponse(
            access_token=new_access_token,
            token_type="bearer",
            user_type="customer",
            user=CustomerResponse(
                id=str(customer.id),
                email=customer.email,
                full_name=customer.full_name,
                is_active=customer.is_active
            )
        )

    logger.warning("Token refresh failed: No valid user found for token")
    logger.info("==== TOKEN REFRESH END (INVALID TOKEN) ====")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials"
    )


@router.post("/logout")
async def logout(request: Request):
    """Logout user (client should remove token)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return {"message": "No active session to logout"}

    token = auth_header.split(" ")[1]

    # Try to get admin first
    admin = await get_admin_from_token(token)
    if admin:
        logger.info(f"🚪 Admin logout: {admin.full_name} ({admin.email}) - ID: {admin.id}")
        # Log logout activity
        activity_log = ActivityLog(
            admin_id=str(admin.id),
            action="logout",
            resource_type="auth",
            details={"user_type": "Admin"}
        )
        await activity_log.insert()
        return {"message": "admin logged out successfully"}

    # Try to get customer
    customer = await get_current_customer_from_token(token)
    if customer:
        logger.info(f"🚪 Customer logout: {customer.full_name} ({customer.email}) - ID: {customer.id}")
        return {"message": "Customer logged out successfully"}

    logger.warning("Logout attempt with invalid token")
    return {"message": "Invalid token"}

