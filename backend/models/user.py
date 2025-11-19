"""
User Model for Admin Authentication and Authorization
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class User(Base):
    """
    User model for admin panel authentication and authorization

    Attributes:
        id: Primary key
        username: Unique username for login
        email: User's email address
        password_hash: Hashed password
        role: User role (admin, moderator, viewer)
        is_active: Whether user account is active
        last_login: Last login timestamp
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        login_attempts: Failed login attempts counter
        locked_until: Account lockout timestamp
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")  # admin, moderator, viewer
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}', active={self.is_active})>"


class AuditLog(Base):
    """
    Audit log for admin actions

    Attributes:
        id: Primary key
        user_id: Reference to user who performed action
        action: Action performed (login, logout, config_change, etc.)
        resource: Resource affected (user, config, system, etc.)
        resource_id: ID of affected resource
        details: JSON details of the action
        ip_address: Client IP address
        user_agent: Client user agent
        timestamp: When action occurred
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)  # JSON string
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}', resource='{self.resource}')>"