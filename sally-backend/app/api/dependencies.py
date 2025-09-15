from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from typing import Optional
from app.core.security import verify_token
from app.domain.entities import User, UserRole

async def get_optional_auth_header(request: Request) -> Optional[HTTPAuthorizationCredentials]:
    """Get authorization header if it exists and is valid, otherwise return None."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    if not token:
        return None
    
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(get_optional_auth_header)) -> User:
    """Get current authenticated user from JWT token."""
    payload = verify_token(credentials.credentials)
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user = await User.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


async def get_current_customer(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is a customer or higher."""
    if current_user.role not in [UserRole.CUSTOMER, UserRole.admin, UserRole.SuperAdmin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is an admin or super admin."""
    if current_user.role not in [UserRole.admin, UserRole.SuperAdmin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin access required"
        )
    return current_user


async def get_current_SuperAdmin(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is a super admin."""
    if current_user.role != UserRole.SuperAdmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_auth_header)) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    if not credentials or not credentials.credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
