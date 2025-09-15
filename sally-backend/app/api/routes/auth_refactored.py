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
        access_token = create_access_token(
            data={"sub": str(admin.id), "type": "admin"}, 
            expires_delta=access_token_expires
        )
        
        # Get admin's role information
        role = await admin.get_role()
        role_name = role.name if role else "unknown"

        # Log login activity
        activity_log = ActivityLog(
            admin_id=str(admin.id),
            action="login",
            resource_type="auth",
            details={"user_type": "admin"}
        )
        await activity_log.insert()

        return UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_type="admin",
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive customer account"
            )
        
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
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/me")
async def get_current_user_info(request: Request):
    """Get current user information (admin or customer)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = auth_header.split(" ")[1]
    
    # Try to get admin first
    admin = await get_admin_from_token(token)
    if admin:
        role = await admin.get_role()
        return {
            "user_type": "admin",
            "user": {
                "id": str(admin.id),
                "email": admin.email,
                "full_name": admin.full_name,
                "role": role.name if role else "unknown",
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
                "is_active": customer.is_active
            }
        }
    
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
        # Log logout activity
        activity_log = ActivityLog(
            admin_id=str(admin.id),
            action="logout",
            resource_type="auth",
            details={"user_type": "admin"}
        )
        await activity_log.insert()
        return {"message": "admin logged out successfully"}
    
    # Try to get customer
    customer = await get_current_customer_from_token(token)
    if customer:
        return {"message": "Customer logged out successfully"}
    
    return {"message": "Invalid token"}

