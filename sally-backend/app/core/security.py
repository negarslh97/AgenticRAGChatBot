from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode JWT token."""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"==== JWT TOKEN VERIFICATION START ====")
    logger.info(f"Token received: {token[:8]}...")
    logger.info(f"Using algorithm: {settings.jwt_algorithm}")

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        logger.info(f"JWT verification successful")
        logger.info(f"Payload: {payload}")
        logger.info("==== JWT TOKEN VERIFICATION END (SUCCESS) ====")
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
