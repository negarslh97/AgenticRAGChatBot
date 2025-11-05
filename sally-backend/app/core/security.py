# security.py

from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings
import logging
from functools import lru_cache

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token cache for authentication optimization
_token_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl = 300  # 5 minutes cache TTL

logger = logging.getLogger(__name__)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, long_lived: bool = False) -> str:
    """Create JWT access token with option for longer expiration."""
    to_encode = data.copy()
    
    if long_lived:
        # Use longer expiration for long-lived tokens (7 days)
        expire = datetime.utcnow() + timedelta(days=7)
        logger.info("Creating long-lived access token (7 days)")
    elif expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Use default expiration (30 days)
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    # Cache the token for faster verification
    _cache_token(encoded_jwt, to_encode)
    
    return encoded_jwt


def _cache_token(token: str, payload: dict):
    """Cache token payload for faster verification."""
    _token_cache[token] = {
        "payload": payload,
        "timestamp": datetime.utcnow(),
        "user_type": payload.get("type", "unknown")
    }
    logger.debug(f"Token cached for user type: {payload.get('type')}")


def _is_token_cached(token: str) -> bool:
    """Check if token is in cache and still valid."""
    cached_data = _token_cache.get(token)
    if not cached_data:
        return False
    
    # Check if cache entry is still valid (within TTL)
    cache_age = (datetime.utcnow() - cached_data["timestamp"]).total_seconds()
    if cache_age > _cache_ttl:
        # Remove expired cache entry
        del _token_cache[token]
        return False
    
    return True


def verify_token(token: str) -> dict:
    """Verify and decode JWT token with caching optimization."""
    logger.info(f"==== JWT TOKEN VERIFICATION START ====")
    logger.info(f"Token received: {token[:8]}...")
    logger.info(f"Using algorithm: {settings.jwt_algorithm}")

    # Check cache first
    if _is_token_cached(token):
        cached_data = _token_cache[token]
        logger.info(f"✅ Token found in cache for user type: {cached_data['user_type']}")
        logger.info("==== JWT TOKEN VERIFICATION END (CACHE HIT) ====")
        return cached_data["payload"]

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        logger.info(f"JWT verification successful")
        logger.info(f"Payload: {payload}")
        logger.info("==== JWT TOKEN VERIFICATION END (SUCCESS) ====")
        
        # Cache the newly verified token
        _cache_token(token, payload)
        
        return payload
    except JWTError as e:
        logger.error(f"JWT verification failed: {str(e)}")
        logger.info("==== JWT TOKEN VERIFICATION END (FAILED) ====")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during JWT verification: {str(e)}")
        logger.info("==== JWT TOKEN VERIFICATION END (ERROR) ====")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_user_type_from_token(token: str) -> str:
    """Extract user type from token without full verification (cache optimized)."""
    # Check cache first
    if _is_token_cached(token):
        return _token_cache[token]["user_type"]
    
    try:
        # For performance, only decode the header to get user type
        import json
        import base64
        
        # Split token into parts
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        
        # Decode payload (without signature verification for performance)
        payload_data = parts[1]
        # Add padding if needed
        payload_data += '=' * (4 - len(payload_data) % 4)
        decoded = base64.urlsafe_b64decode(payload_data)
        payload = json.loads(decoded.decode('utf-8'))
        
        user_type = payload.get("type", "unknown")
        logger.debug(f"User type extracted from token: {user_type}")
        return user_type
        
    except Exception as e:
        logger.warning(f"Failed to extract user type from token: {e}")
        return "unknown"


def clear_token_cache():
    """Clear all cached tokens (useful for logout or security updates)."""
    global _token_cache
    cache_size = len(_token_cache)
    _token_cache = {}
    logger.info(f"Token cache cleared: {cache_size} entries removed")


def get_user_info_from_token(token: str) -> Tuple[str, Dict[str, Any]]:
    """
    Unified function to extract user information from token based on user type.
    
    This function optimizes user identification by:
    1. Checking cache first
    2. Extracting user type quickly
    3. Returning appropriate user information structure
    
    Args:
        token: JWT token string
        
    Returns:
        Tuple of (user_type, user_info)
        
    Raises:
        HTTPException: If token is invalid
    """
    logger.info(f"==== USER INFO EXTRACTION START ====")
    logger.info(f"Token received: {token[:8]}...")
    
    # Check cache first
    if _is_token_cached(token):
        cached_data = _token_cache[token]
        user_type = cached_data["user_type"]
        payload = cached_data["payload"]
        
        logger.info(f"✅ User info found in cache: {user_type}")
        logger.info("==== USER INFO EXTRACTION END (CACHE HIT) ====")
        
        return user_type, payload
    
    try:
        # Full token verification
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_type = payload.get("type", "unknown")
        
        logger.info(f"✅ User info extracted: {user_type}")
        logger.info(f"Payload: {payload}")
        logger.info("==== USER INFO EXTRACTION END (SUCCESS) ====")
        
        # Cache the result
        _cache_token(token, payload)
        
        return user_type, payload
        
    except JWTError as e:
        logger.error(f"JWT verification failed: {str(e)}")
        logger.info("==== USER INFO EXTRACTION END (FAILED) ====")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during user info extraction: {str(e)}")
        logger.info("==== USER INFO EXTRACTION END (ERROR) ====")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def should_skip_user_type_check(user_type: str, target_types: list) -> bool:
    """
    Determine if user type check should be skipped based on optimization rules.
    
    Args:
        user_type: Current user type
        target_types: List of allowed user types
        
    Returns:
        True if check should be skipped, False otherwise
    """
    # Optimization: Skip redundant checks for same user type
    if user_type in target_types:
        logger.debug(f"User type {user_type} matches target types, skipping redundant check")
        return True
    
    return False
