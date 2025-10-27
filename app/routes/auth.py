"""
Authentication middleware and utilities for admin access.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.core.supabase import get_supabase_client
from app.core.config import get_settings
from app.models.schemas import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    UserResponse
)

# Get settings
settings = get_settings()

# JWT Configuration from settings
JWT_SECRET = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
JWT_EXPIRATION_MINUTES = settings.jwt_expiration_minutes

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
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
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

async def check_is_admin(user_id: str) -> bool:
    """
    Check if a user has admin access in the admin_users table.

    Args:
        user_id: User's UUID from auth.users

    Returns:
        True if user is an active admin, False otherwise
    """
    supabase = get_supabase_client(use_service_key=True)
    try:
        response = supabase.table("admin_users").select("*").eq("user_id", user_id).eq("is_active", True).is_("revoked_at", "null").execute()
        return len(response.data) > 0 if response.data else False
    except Exception as e:
        print(f"[ERROR] Failed to check admin status: {e}")
        return False

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token.
    Verifies both authentication AND admin access.

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        User data dictionary with id and email

    Raises:
        HTTPException: If authentication fails or user is not an admin
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

    # Check if user has admin access
    is_admin = await check_is_admin(user_id)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required. Please contact support to request access."
        )

    return {
        "id": user_id,
        "email": email,
        "is_admin": True
    }

async def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """
    Authenticate user with email and password using Supabase Auth.
    Also verifies user has admin access in admin_users table.

    Args:
        email: User's email address
        password: User's password

    Returns:
        Dictionary with user data and access token

    Raises:
        HTTPException: If authentication fails or user is not an admin
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

        # Check if user has admin access
        is_admin = await check_is_admin(response.user.id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Your account does not have admin privileges. Please contact support to request access."
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


# ============================================================================
# ROUTER SETUP
# ============================================================================

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Admin login endpoint

    Authenticates user with Supabase Auth and returns JWT token
    """
    try:
        auth_result = await authenticate_user(
            email=credentials.email,
            password=credentials.password
        )

        return LoginResponse(
            success=True,
            data=TokenResponse(
                access_token=auth_result["access_token"],
                token_type=auth_result["token_type"],
                user=UserResponse(
                    id=auth_result["user"]["id"],
                    email=auth_result["user"]["email"]
                )
            )
        )

    except HTTPException as e:
        return LoginResponse(
            success=False,
            error=e.detail
        )
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        return LoginResponse(
            success=False,
            error="Authentication failed"
        )


@router.post("/signup", response_model=SignupResponse)
async def signup(credentials: SignupRequest):
    """
    User signup endpoint

    Creates a new user in Supabase Auth. User will not have admin access until manually granted in Supabase dashboard.
    """
    try:
        supabase = get_supabase_client(use_service_key=False)

        # Create user in Supabase Auth
        response = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password
        })

        if response.user:
            return SignupResponse(
                success=True,
                message="Conta criada com sucesso! Você pode fazer login agora. Nota: Acesso administrativo será concedido manualmente."
            )
        else:
            return SignupResponse(
                success=False,
                error="Falha ao criar conta. Por favor, tente novamente."
            )

    except Exception as e:
        error_message = str(e)
        print(f"[ERROR] Signup error: {error_message}")

        # Check for common errors
        if "already registered" in error_message.lower() or "already exists" in error_message.lower():
            return SignupResponse(
                success=False,
                error="Este email já está registrado. Faça login ou use outro email."
            )

        return SignupResponse(
            success=False,
            error="Erro ao criar conta. Por favor, tente novamente."
        )
