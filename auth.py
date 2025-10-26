"""
Authentication middleware and utilities for admin access.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from supabase_client import get_supabase_client
from dotenv import load_dotenv

load_dotenv()

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security scheme
security = HTTPBearer()

def create_access_token(user_id: str, email: str) -> str:
    """
    Create JWT access token for authenticated user.

    Args:
        user_id: User's unique identifier
        email: User's email address

    Returns:
        JWT token string
    """
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        User data dictionary with id and email

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = verify_token(token)

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Verify user still exists in Supabase
    supabase = get_supabase_client(use_service_key=True)
    try:
        response = supabase.auth.admin.get_user_by_id(user_id)
        if not response:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )

    return {
        "id": user_id,
        "email": email
    }

async def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """
    Authenticate user with email and password using Supabase Auth.

    Args:
        email: User's email address
        password: User's password

    Returns:
        Dictionary with user data and access token

    Raises:
        HTTPException: If authentication fails
    """
    supabase = get_supabase_client(use_service_key=False)

    try:
        # Authenticate with Supabase
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Create our own JWT token for subsequent requests
        access_token = create_access_token(
            user_id=response.user.id,
            email=response.user.email
        )

        return {
            "user": {
                "id": response.user.id,
                "email": response.user.email
            },
            "access_token": access_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

# Dependency for protected routes
RequireAuth = Depends(get_current_user)
