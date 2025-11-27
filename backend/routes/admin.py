"""
Admin Routes for MAMcrawler Admin Panel
FastAPI router for admin authentication, user management, and system administration
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field, EmailStr, field_validator
import jwt

from backend.database import get_db
from backend.models.user import User, AuditLog
from backend.config import get_settings
from backend.rate_limit import limiter, get_rate_limit

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Get settings
settings = get_settings()

# JWT Configuration
JWT_SECRET_KEY = settings.JWT_SECRET_KEY or secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security scheme
security = HTTPBearer(auto_error=False)


# ============================================================================
# Pydantic Models
# ============================================================================

class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    expires_in: int


class UserCreateRequest(BaseModel):
    """User creation request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field("viewer", pattern="^(admin|moderator|viewer)$")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("admin", "moderator", "viewer"):
            raise ValueError("Invalid role")
        return v


class UserUpdateRequest(BaseModel):
    """User update request"""
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, pattern="^(admin|moderator|viewer)$")
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v is not None and v not in ("admin", "moderator", "viewer"):
            raise ValueError("Invalid role")
        return v


class PasswordChangeRequest(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str = Field(..., min_length=8)


class StandardResponse(BaseModel):
    """Standard API response"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================================
# Utility Functions
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt"""
    salt = settings.PASSWORD_SALT or "mamcrawler_salt"
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    return hash_password(password) == password_hash


def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin role"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def require_moderator_or_admin(user: User = Depends(get_current_user)) -> User:
    """Require moderator or admin role"""
    if user.role not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator or admin access required"
        )
    return user


def log_admin_action(
    db: Session,
    user: User,
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """Log admin action to audit log"""
    try:
        audit_log = AuditLog(
            user_id=user.id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")


# ============================================================================
# Authentication Routes
# ============================================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Admin login",
    description="Authenticate admin user and return JWT token"
)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token"""
    try:
        # Find user
        user = db.query(User).filter(
            and_(
                User.username == login_data.username,
                User.is_active == True
            )
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to failed login attempts"
            )

        # Verify password
        if not verify_password(login_data.password, user.password_hash):
            # Increment failed attempts
            user.login_attempts += 1

            # Lock account after 5 failed attempts
            if user.login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)

            db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Reset failed attempts and update last login
        user.login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        db.commit()

        # Create access token
        access_token = create_access_token({"user_id": user.id, "username": user.username})

        # Log successful login
        log_admin_action(
            db, user, "login", "auth", str(user.id),
            {"username": user.username}, request
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/logout",
    response_model=StandardResponse,
    summary="Admin logout",
    description="Log out current admin user"
)
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Log out user (client should discard token)"""
    try:
        # Log logout action
        log_admin_action(
            db, user, "logout", "auth", str(user.id),
            {"username": user.username}, request
        )

        return {
            "success": True,
            "data": {"message": "Logged out successfully"},
            "error": None
        }

    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/me",
    response_model=StandardResponse,
    summary="Get current user info",
    description="Get information about the currently authenticated user"
)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "success": True,
        "data": {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat()
            }
        },
        "error": None
    }


# ============================================================================
# User Management Routes
# ============================================================================

@router.get(
    "/users",
    response_model=StandardResponse,
    summary="List users",
    description="Get list of all users (admin only)"
)
async def list_users(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users"""
    try:
        users = db.query(User).all()

        user_list = []
        for u in users:
            user_list.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat(),
                "login_attempts": u.login_attempts,
                "locked_until": u.locked_until.isoformat() if u.locked_until else None
            })

        return {
            "success": True,
            "data": {"users": user_list},
            "error": None
        }

    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/users",
    response_model=StandardResponse,
    summary="Create user",
    description="Create a new user account (admin only)"
)
async def create_user(
    request: Request,
    user_data: UserCreateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new user"""
    try:
        # Check if username or email already exists
        existing = db.query(User).filter(
            or_(
                User.username == user_data.username,
                User.email == user_data.email
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )

        # Create new user
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            role=user_data.role
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Log user creation
        log_admin_action(
            db, current_user, "create", "user", str(new_user.id),
            {"username": new_user.username, "role": new_user.role}, request
        )

        return {
            "success": True,
            "data": {
                "user": {
                    "id": new_user.id,
                    "username": new_user.username,
                    "email": new_user.email,
                    "role": new_user.role,
                    "is_active": new_user.is_active,
                    "created_at": new_user.created_at.isoformat()
                },
                "message": "User created successfully"
            },
            "error": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/users/{user_id}",
    response_model=StandardResponse,
    summary="Get user details",
    description="Get detailed information about a specific user"
)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db)
):
    """Get user details"""
    try:
        target_user = db.query(User).filter(User.id == user_id).first()

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Users can view their own info, moderators/admins can view all
        if current_user.role not in ["admin", "moderator"] and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return {
            "success": True,
            "data": {
                "user": {
                    "id": target_user.id,
                    "username": target_user.username,
                    "email": target_user.email,
                    "role": target_user.role,
                    "is_active": target_user.is_active,
                    "last_login": target_user.last_login.isoformat() if target_user.last_login else None,
                    "created_at": target_user.created_at.isoformat(),
                    "updated_at": target_user.updated_at.isoformat(),
                    "login_attempts": target_user.login_attempts,
                    "locked_until": target_user.locked_until.isoformat() if target_user.locked_until else None
                }
            },
            "error": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put(
    "/users/{user_id}",
    response_model=StandardResponse,
    summary="Update user",
    description="Update user information (admin only)"
)
async def update_user(
    user_id: int,
    request: Request,
    user_data: UserUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user information"""
    try:
        target_user = db.query(User).filter(User.id == user_id).first()

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Track changes for audit log
        changes = {}

        # Update fields
        if user_data.email is not None and user_data.email != target_user.email:
            # Check email uniqueness
            existing = db.query(User).filter(
                and_(User.email == user_data.email, User.id != user_id)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists"
                )
            target_user.email = user_data.email
            changes["email"] = user_data.email

        if user_data.role is not None and user_data.role != target_user.role:
            target_user.role = user_data.role
            changes["role"] = user_data.role

        if user_data.is_active is not None and user_data.is_active != target_user.is_active:
            target_user.is_active = user_data.is_active
            changes["is_active"] = user_data.is_active

        target_user.updated_at = datetime.utcnow()
        db.commit()

        # Log user update
        if changes:
            log_admin_action(
                db, current_user, "update", "user", str(user_id),
                {"changes": changes}, request
            )

        return {
            "success": True,
            "data": {
                "user": {
                    "id": target_user.id,
                    "username": target_user.username,
                    "email": target_user.email,
                    "role": target_user.role,
                    "is_active": target_user.is_active,
                    "updated_at": target_user.updated_at.isoformat()
                },
                "message": "User updated successfully"
            },
            "error": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete(
    "/users/{user_id}",
    response_model=StandardResponse,
    summary="Delete user",
    description="Delete a user account (admin only)"
)
async def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a user"""
    try:
        target_user = db.query(User).filter(User.id == user_id).first()

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Prevent deleting self
        if target_user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )

        # Store user info for audit log
        user_info = {
            "username": target_user.username,
            "email": target_user.email,
            "role": target_user.role
        }

        # Delete user
        db.delete(target_user)
        db.commit()

        # Log user deletion
        log_admin_action(
            db, current_user, "delete", "user", str(user_id),
            user_info, request
        )

        return {
            "success": True,
            "data": {"message": "User deleted successfully"},
            "error": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/users/{user_id}/password",
    response_model=StandardResponse,
    summary="Change password",
    description="Change user password"
)
async def change_password(
    user_id: int,
    request: Request,
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    try:
        target_user = db.query(User).filter(User.id == user_id).first()

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Users can change their own password, admins can change any password
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # For non-admin users changing their own password, verify current password
        if current_user.role != "admin" and current_user.id == user_id:
            if not verify_password(password_data.current_password, target_user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )

        # Update password
        target_user.password_hash = hash_password(password_data.new_password)
        target_user.updated_at = datetime.utcnow()
        db.commit()

        # Log password change
        log_admin_action(
            db, current_user, "password_change", "user", str(user_id),
            {"changed_by": current_user.username}, request
        )

        return {
            "success": True,
            "data": {"message": "Password changed successfully"},
            "error": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ============================================================================
# Audit Log Routes
# ============================================================================

@router.get(
    "/audit-logs",
    response_model=StandardResponse,
    summary="Get audit logs",
    description="Get admin action audit logs (admin only)"
)
async def get_audit_logs(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get audit logs with optional filtering"""
    try:
        query = db.query(AuditLog)

        # Apply filters
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource:
            query = query.filter(AuditLog.resource == resource)

        # Get total count
        total_count = query.count()

        # Apply pagination
        logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

        log_list = []
        for log in logs:
            log_list.append({
                "id": log.id,
                "user_id": log.user_id,
                "username": log.user.username if log.user else "Unknown",
                "action": log.action,
                "resource": log.resource,
                "resource_id": log.resource_id,
                "details": json.loads(log.details) if log.details else None,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "timestamp": log.timestamp.isoformat()
            })

        return {
            "success": True,
            "data": {
                "logs": log_list,
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            },
            "error": None
        }

    except Exception as e:
        logger.error(f"Error getting audit logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )