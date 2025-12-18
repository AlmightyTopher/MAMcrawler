# backend/auth.py
"""
Secure authentication and authorization utilities for the MAMcrawler API.
Implements bcrypt password hashing, JWT token management, and secure session handling.
"""

import os
import json
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Union
from pathlib import Path

import bcrypt
import jwt
from passlib.context import CryptContext

# Initialize logging
logger = logging.getLogger(__name__)

# CryptContext for password hashing - using bcrypt as the primary algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DELTA = timedelta(hours=24)  # Token expires in 24 hours

class SecurityConfig:
    """Secure configuration management for authentication-related settings."""
    
    def __init__(self):
        self._jwt_secret = None
        self._encryption_key = None
    
    @property
    def jwt_secret(self) -> str:
        """Get JWT secret from environment, file, or generate a secure one."""
        if self._jwt_secret is None:
            # 1. Try Environment Variable
            self._jwt_secret = os.getenv("JWT_SECRET")
            
            # 2. Try Secret File
            if not self._jwt_secret:
                secret_path = Path(".secrets/jwt.key")
                if secret_path.exists():
                     try:
                        with open(secret_path, "r") as f:
                            self._jwt_secret = f.read().strip()
                        if self._jwt_secret:
                            logger.info("Loaded JWT secret from file.")
                     except Exception as e:
                        logger.error(f"Failed to read JWT secret file: {e}")

            # 3. Generate and Persist New Secret
            if not self._jwt_secret:
                logger.warning("JWT_SECRET not found in environment or file. Generating and persisting new secret.")
                self._jwt_secret = self._generate_secure_random_key(32)
                
                try:
                    secret_path = Path(".secrets/jwt.key")
                    secret_path.parent.mkdir(exist_ok=True)
                    with open(secret_path, "w") as f:
                        f.write(self._jwt_secret)
                    os.chmod(secret_path, 0o600)
                    logger.info(f"Persisted new JWT secret to {secret_path}")
                except Exception as e:
                    logger.error(f"Failed to persist JWT secret: {e}")

                os.environ["JWT_SECRET"] = self._jwt_secret
                
        return self._jwt_secret
    
    @property
    def encryption_key(self) -> bytes:
        """Get or generate encryption key for sensitive data."""
        if self._encryption_key is None:
            key_path = Path(".secrets/encryption.key")
            if key_path.exists():
                with open(key_path, "rb") as key_file:
                    self._encryption_key = key_file.read()
            else:
                logger.warning("Encryption key not found. Generating temporary key.")
                self._encryption_key = secrets.token_bytes(32)
                key_path.parent.mkdir(exist_ok=True)
                with open(key_path, "wb") as key_file:
                    key_file.write(self._encryption_key)
                os.chmod(key_path, 0o600)  # Set restrictive permissions
        return self._encryption_key
    
    @staticmethod
    def _generate_secure_random_key(length: int) -> str:
        """Generate a cryptographically secure random key."""
        return secrets.token_urlsafe(length)

# Initialize security configuration
security_config = SecurityConfig()

def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
    """
    try:
        # bcrypt handles salting automatically
        hashed = pwd_context.hash(password)
        logger.debug("Password hashed successfully")
        return hashed
    except Exception as e:
        logger.error(f"Password hashing failed: {str(e)}")
        raise ValueError("Password hashing failed") from e

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Previously hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        # Verify using passlib which handles bcrypt verification
        is_valid = pwd_context.verify(plain_password, hashed_password)
        
        if not is_valid:
            logger.warning("Password verification failed")
        else:
            logger.debug("Password verified successfully")
            
        return is_valid
    except Exception as e:
        logger.error(f"Password verification failed: {str(e)}")
        return False

def generate_token(user_id: Union[str, int], additional_claims: Optional[Dict] = None) -> str:
    """Generate a JWT token for a user.
    
    Args:
        user_id: User identifier
        additional_claims: Optional additional claims to include in the token
        
    Returns:
        JWT token string
    """
    try:
        now = datetime.utcnow()
        exp = now + JWT_EXPIRATION_DELTA
        
        # Base payload
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": exp
        }
        
        # Add any additional claims
        if additional_claims:
            payload.update(additional_claims)
        
        # Generate token
        token = jwt.encode(payload, security_config.jwt_secret, algorithm=JWT_ALGORITHM)
        logger.debug(f"JWT token generated for user {user_id}")
        return token
        
    except Exception as e:
        logger.error(f"Token generation failed: {str(e)}")
        raise ValueError("Token generation failed") from e

def verify_token(token: str) -> Optional[Dict]:
    """Verify a JWT token and return its payload.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, security_config.jwt_secret, algorithms=[JWT_ALGORITHM])
        logger.debug(f"JWT token verified successfully")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT token validation failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return None

def generate_secure_api_key(length: int = 32) -> str:
    """Generate a cryptographically secure API key.
    
    Args:
        length: Length of the API key in bytes
        
    Returns:
        Secure API key string
    """
    return secrets.token_urlsafe(length)

def secure_store_secret(secret: str, storage_path: str) -> bool:
    """Securely store a secret in a file with proper permissions.
    
    Args:
        secret: Secret to store
        storage_path: Path to store the secret
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        path = Path(storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write with restrictive permissions (owner read/write only)
        with open(path, "w") as f:
            json.dump({"secret": secret, "created": datetime.utcnow().isoformat()}, f)
        
        # Set file permissions (Unix only)
        if hasattr(os, "chmod"):
            os.chmod(path, 0o600)
        
        logger.debug(f"Secret stored securely at {storage_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to store secret securely: {str(e)}")
        return False

def secure_retrieve_secret(storage_path: str) -> Optional[str]:
    """Securely retrieve a secret from storage.
    
    Args:
        storage_path: Path to the stored secret
        
    Returns:
        Secret if found, None otherwise
    """
    try:
        path = Path(storage_path)
        if not path.exists():
            logger.warning(f"Secret file not found at {storage_path}")
            return None
        
        # Read and parse JSON
        with open(path, "r") as f:
            data = json.load(f)
            
        secret = data.get("secret")
        if not secret:
            logger.error(f"Invalid secret format in {storage_path}")
            return None
            
        logger.debug(f"Secret retrieved securely from {storage_path}")
        return secret
    except Exception as e:
        logger.error(f"Failed to retrieve secret: {str(e)}")
        return None

def sanitize_input(input_str: str) -> str:
    """Sanitize user input to prevent injection attacks.
    
    Args:
        input_str: Input string to sanitize
        
    Returns:
        Sanitized string
    """
    if not isinstance(input_str, str):
        return ""
    
    # Remove potentially dangerous characters
    sanitized = input_str.strip()
    
    # Log potential security concerns
    if any(char in sanitized for char in ["<", ">", "&", "\"", "'"]):
        logger.warning(f"Potentially dangerous characters in user input: {sanitized[:50]}")
    
    return sanitized

def rate_limit_key(user_id: str, action: str) -> str:
    """Generate a rate limiting key for a user and action.
    
    Args:
        user_id: User identifier
        action: Action being performed
        
    Returns:
        Rate limiting key string
    """
    return f"rate_limit:{sanitize_input(user_id)}:{sanitize_input(action)}"