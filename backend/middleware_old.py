# backend/middleware.py
"""
Security middleware for the MAMcrawler API.
Implements CORS policies, security headers, and request validation.
"""

import os
import logging
import secrets
from typing import List, Optional, Set
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time

# Configure logging
logger = logging.getLogger(__name__)

# Allowed origins for CORS - should be configured via environment variables
ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS", "").strip()
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",") if origin.strip()] if ALLOWED_ORIGINS_ENV else []

# Allowed hosts for the application
ALLOWED_HOSTS_ENV = os.getenv("ALLOWED_HOSTS", "").strip()
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_ENV.split(",") if host.strip()] if ALLOWED_HOSTS_ENV else []

# API key for securing sensitive endpoints
API_KEY = os.getenv("API_KEY")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to all responses.
    Implements OWASP recommended security headers.
    """
    
    def __init__(self, app: FastAPI, allowed_hosts: Optional[List[str]] = None):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or ["localhost", "127.0.0.1"]
        
        # Nonce for Content Security Policy (CSP) - random per instance
        self.nonce = secrets.token_hex(16)
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Validate host header to prevent host header injection
        host = request.headers.get("host", "")
        if host:
            # Remove port from host header for validation (e.g., "localhost:8000" -> "localhost")
            host_without_port = host.split(":")[0]
            if host_without_port not in self.allowed_hosts:
                logger.warning(f"Blocked request with invalid host header: {host}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid host header"}
                )
        
        # Process the request
        response = await call_next(request)
        
        # Add security headers
        headers = response.headers
        
        # Content Security Policy (CSP) - prevents XSS attacks
        # This is a restrictive policy, adjust as needed
        csp = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{self.nonce}'; "
            f"style-src 'self' 'unsafe-inline'; "
            f"img-src 'self' data: https:; "
            f"font-src 'self' https:; "
            f"connect-src 'self' https:; "
            f"frame-ancestors 'none'; "
            f"form-action 'self';"
        )
        headers["Content-Security-Policy"] = csp
        
        # X-Content-Type-Options - prevents MIME sniffing
        headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options - prevents clickjacking
        headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection - enables browser XSS filter
        headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy - controls referrer information
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS - forces HTTPS connections
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Permissions-Policy - controls browser features
        headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )
        
        # Cache-Control for API responses
        if request.url.path.startswith("/api/"):
            headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        
        # X-API-Version (for API requests)
        if request.url.path.startswith("/api/"):
            headers["X-API-Version"] = "1.0"

        # Remove server information (use del for MutableHeaders)
        if "server" in headers:
            del headers["server"]
        
        # Add response time header for monitoring
        process_time = time.time() - start_time
        headers["X-Process-Time"] = str(process_time)
        
        return response

def add_cors_middleware(app: FastAPI) -> None:
    """
    Add CORS middleware to the FastAPI app with strict security policies.

    Args:
        app: FastAPI application instance
    """
    # Default to denying all origins if not explicitly configured
    allow_origins = ALLOWED_ORIGINS if ALLOWED_ORIGINS else ["https://example.com"]  # Dummy URL that will be rejected in production

    # Log warning if using permissive CORS settings
    if not ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS:
        logger.warning("CORS is configured permissively or with wildcard. This is not recommended for production.")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Requested-With",
            "Accept",
            "Origin",
            "X-API-Key"
        ],
        expose_headers=[
            "X-Total-Count",
            "X-Process-Time",
            "X-API-Version"
        ],
        max_age=600,  # Cache preflight requests for 10 minutes
    )

def verify_api_key(request: Request) -> bool:
    """
    Verify API key in request headers for sensitive endpoints.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if API key is valid or not required, False otherwise
    """
    # If API key is not configured, don't require it
    if not API_KEY:
        return True
    
    # Get API key from header
    request_api_key = request.headers.get("X-API-Key")
    
    # Compare securely using secrets.compare_digest to prevent timing attacks
    if request_api_key and secrets.compare_digest(request_api_key, API_KEY):
        logger.debug("API key verified successfully")
        return True
    
    logger.warning("Invalid or missing API key")
    return False

def validate_file_upload(request: Request) -> bool:
    """
    Validate file uploads to prevent malicious files.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if file appears safe, False otherwise
    """
    # Get content type
    content_type = request.headers.get("content-type", "")
    
    # Only allow specific content types for uploads
    allowed_types = [
        "application/json",
        "application/pdf",
        "text/csv",
        "text/plain",
        "application/octet-stream"  # For binary files like images
    ]
    
    for allowed_type in allowed_types:
        if content_type.startswith(allowed_type):
            logger.debug(f"File upload validated with content type: {content_type}")
            return True
    
    logger.warning(f"Rejected file upload with content type: {content_type}")
    return False

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests with security-sensitive information.
    """
    
    def __init__(self, app: FastAPI, sensitive_paths: Optional[Set[str]] = None):
        super().__init__(app)
        self.sensitive_paths = sensitive_paths or {"/api/admin", "/api/auth", "/api/downloads"}
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Create a request identifier for tracking
        request_id = secrets.token_hex(8)
        
        # Get client information (with privacy considerations)
        client_ip = request.client.host if request.client else "unknown"
        
        # Log request (with sanitized path for sensitive routes)
        path = request.url.path
        sanitized_path = path if path not in self.sensitive_paths else f"{path} (sanitized)"
        
        logger.info(f"Request: {request_id} {request.method} {sanitized_path} from {client_ip}")
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response (with status code only for sensitive routes)
        if path in self.sensitive_paths:
            logger.info(f"Response: {request_id} {response.status_code} (processed in {process_time:.3f}s)")
        else:
            logger.debug(f"Response: {request_id} {response.status_code} (processed in {process_time:.3f}s)")
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response

def setup_security_middleware(app: FastAPI) -> None:
    """
    Configure all security middleware for the application.

    Args:
        app: FastAPI application instance
    """
    # Add CORS middleware
    add_cors_middleware(app)

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware, allowed_hosts=ALLOWED_HOSTS)

    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    logger.info("Security middleware configured successfully")

# Add to environment template
ENV_TEMPLATE = """
# Security Configuration
JWT_SECRET=your_super_secret_jwt_key_change_this_in_production
API_KEY=your_secure_api_key_for_admin_endpoints

# CORS Configuration (comma-separated list)
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# Allowed Hosts (comma-separated list)
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Encryption key for sensitive data storage
# Leave empty to generate automatically on startup
ENCRYPTION_KEY=

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
"""