from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.domain.entities import User, UserRole, ActivityLog
from app.api.dependencies import get_current_user
from fastapi import Request
import logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify the API is working."""
    return {"message": "Auth API is working!"}


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


@router.post("/register", response_model=UserResponse)
async def register(request: Request):
    """Register a new customer user."""
    logger.info(f"Register endpoint called with content-type: {request.headers.get('content-type')}")
    
    try:
        # Handle both JSON and FormData
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # Handle JSON request
            json_data = await request.json()
            logger.info(f"JSON data: {json_data}")
            email = json_data.get("email")
            password = json_data.get("password")
            full_name = json_data.get("full_name")
        elif "multipart/form-data" in content_type:
            # Handle FormData request
            form = await request.form()
            logger.info(f"FormData: {dict(form)}")
            email = form.get("username")  # FastAPI OAuth2 uses username for email
            password = form.get("password")
            full_name = ""  # Not available in form data
        else:
            logger.error(f"Unsupported content type: {content_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported content type"
            )
        
        logger.info(f"Register attempt with email: {email}")
        
        if not email or not password:
            logger.error("Email or password missing")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )
        
    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )
    
    # Check if user already exists
    existing_user = await User.find_one(User.email == email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name or email.split('@')[0],  # Use email prefix as name if not provided
        role=UserRole.CUSTOMER
    )
    
    try:
        await user.insert()
    except Exception as e:
        # If duplicate key error, try to clean up the database first
        if "duplicate key" in str(e):
            # Drop the unique index on username if it exists
            from motor.motor_asyncio import AsyncIOMotorClient
            from app.core.config import settings
            client = AsyncIOMotorClient(settings.database_url)
            db = client.get_default_database()
            await db.users.drop_index("username_1")
            await user.insert()
        else:
            raise e
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active
    )


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return JWT token."""
    user = await User.find_one(User.email == form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    # Log login activity
    if user.role in [UserRole.admin, UserRole.SuperAdmin]:
        activity_log = ActivityLog(
            user_id=str(user.id),
            action="login",
            resource_type="auth",
            details={"role": user.role}
        )
        await activity_log.insert()
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should remove token)."""
    # Log logout activity for admin users
    if current_user.role in [UserRole.admin, UserRole.SuperAdmin]:
        activity_log = ActivityLog(
            user_id=str(current_user.id),
            action="logout",
            resource_type="auth",
            details={"role": current_user.role}
        )
        await activity_log.insert()
    
    return {"message": "Successfully logged out"}
