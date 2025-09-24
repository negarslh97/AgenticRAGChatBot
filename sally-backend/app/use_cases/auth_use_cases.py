from typing import Optional
from app.domain.entities_refactored import Role
from app.core.security import verify_password, get_password_hash


class AuthUseCases:
    @staticmethod
    async def authenticate_user(email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await User.find_one(User.email == email)
        
        if not user or not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    @staticmethod
    async def create_user(email: str, password: str, full_name: str, role: UserRole = UserRole.CUSTOMER) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = await User.find_one(User.email == email)
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create new user
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=role
        )
        
        await user.insert()
        return user
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[User]:
        """Get user by ID."""
        return await User.get(user_id)
    
    @staticmethod
    async def update_user_role(user_id: str, new_role: UserRole) -> Optional[User]:
        """Update user role."""
        user = await User.get(user_id)
        if not user:
            return None
        
        user.role = new_role
        await user.save()
        return user
