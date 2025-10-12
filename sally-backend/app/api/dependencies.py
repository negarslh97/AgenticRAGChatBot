from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from typing import Optional, Union, Callable
from app.core.permissions import get_optional_auth_header, get_admin_from_token, get_current_customer_from_token, Permission, has_permission
from app.domain.entities import Admin, Customer


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_auth_header)) -> Union[Admin, Customer]:
    """Get current authenticated user from JWT token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required"
        )

    admin = await get_admin_from_token(credentials.credentials)
    if admin:
        return admin

    customer = await get_current_customer_from_token(credentials.credentials)
    if customer:
        return customer

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials"
    )


async def get_current_customer(current_user: Union[Admin, Customer] = Depends(get_current_user)) -> Customer:
    """Ensure current user is a customer."""
    if isinstance(current_user, Customer):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Customer access required"
    )


async def get_current_admin(current_user: Union[Admin, Customer] = Depends(get_current_user)) -> Admin:
    """Ensure current user is an admin or super admin."""
    if isinstance(current_user, Admin):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )


async def get_current_SuperAdmin(current_user: Union[Admin, Customer] = Depends(get_current_user)) -> Admin:
    """Ensure current user is a super admin."""
    if isinstance(current_user, Admin) and current_user.role_name == "SuperAdmin":
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Super admin access required"
    )


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_auth_header)) -> Optional[Union[Admin, Customer]]:
    """Get current user if authenticated, otherwise return None."""
    if not credentials or not credentials.credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def get_current_admin_with_permission(required_permission: Permission) -> Callable:
    """
    Dependency factory for checking admin permissions.
    
    Usage:
        @router.post("/some-route")
        async def some_endpoint(
            current_admin: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
        ):
            ...
    """
    async def permission_checker(current_admin: Admin = Depends(get_current_admin)) -> Admin:
        """Check if admin has required permission."""
        if not await has_permission(current_admin, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {required_permission.value}"
            )
        return current_admin
    
    return permission_checker
