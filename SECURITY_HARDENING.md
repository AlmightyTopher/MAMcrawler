# MAMcrawler Security Hardening Guide

## Overview

This guide provides comprehensive security hardening measures for the MAMcrawler project, addressing critical security vulnerabilities and implementing industry best practices. The implemented measures align with the OWASP Top 10 security risks and include password security, authentication, API security, and data protection.

## Implemented Security Measures

### 1. Authentication & Authorization

#### API Key Security
- **Implementation**: `backend/auth.py`
- **Features**:
  - Cryptographically secure API key generation
  - Secure storage with proper file permissions
  - Timing-safe comparison to prevent timing attacks
  - Input sanitization for API keys

#### JWT Token Security
- **Implementation**: `backend/auth.py`
- **Features**:
  - Secure JWT token generation with configurable expiration
  - Timing-safe token verification
  - Support for additional claims in tokens
  - Proper error handling without information leakage

### 2. Password Security

#### Password Hashing
- **Implementation**: `backend/auth.py`
- **Features**:
  - bcrypt password hashing (configurable as argon2-cffi)
  - Automatic salt generation
  - Verification without timing attacks
  - Secure password storage patterns

### 3. CORS & Security Headers

#### CORS Configuration
- **Implementation**: `backend/middleware.py`
- **Features**:
  - Configurable allowed origins
  - Strict credential policies
  - Limited allowed methods and headers
  - Proper handling of preflight requests

#### Security Headers
- **Implementation**: `backend/middleware.py`, `backend/main.py`
- **Features**:
  - Content Security Policy (CSP)
  - X-Content-Type-Options
  - X-Frame-Options
  - X-XSS-Protection
  - Referrer-Policy
  - Strict-Transport-Security (HSTS)
  - Permissions-Policy

### 4. Input Validation & Sanitization

#### Input Sanitization
- **Implementation**: `backend/auth.py`
- **Features**:
  - User input sanitization to prevent injection attacks
  - Special character detection and logging
  - Safe string handling patterns

#### Path Traversal Prevention
- **Implementation**: `backend/main.py`
- **Features**:
  - Detection of path traversal patterns in URLs
  - Protection against directory traversal attacks
  - Proper request rejection with appropriate error codes

### 5. Logging & Monitoring

#### Security Logging
- **Implementation**: `backend/middleware.py`
- **Features**:
  - Request/response logging with security-sensitive information handling
  - Rate limiting key generation for tracking
  - Request ID generation for traceability
  - Sensitive path sanitization in logs

### 6. Environment Configuration

#### Secure Environment Variables
- **Implementation**: `.env.template`
- **Features**:
  - Comprehensive template for environment variables
  - Security-related configuration options
  - Proper default values for security settings
  - Documentation of all configuration options

## Additional Security Hardening Recommendations

### 1. Database Security

#### SQL Injection Prevention
- **Recommendation**: Implement parameterized queries for all database operations
- **Implementation**: Use SQLAlchemy's ORM with proper query construction
- **Code Example**:
  ```python
  # Bad (vulnerable to SQL injection)
  query = f"SELECT * FROM users WHERE username = '{username}'"
  
  # Good (protected against SQL injection)
  query = select(User).where(User.username == username)
  ```

#### Database Connection Security
- **Recommendation**: Use SSL for database connections
- **Implementation**: Configure connection with `sslmode=require` in the connection string
- **Code Example**:
  ```python
  DATABASE_URL = "postgresql://user:password@localhost:5432/dbname?sslmode=require"
  ```

#### Database Access Control
- **Recommendation**: Implement proper database user privileges
- **Implementation**: Create database users with minimal required privileges

### 2. API Security

#### API Rate Limiting
- **Recommendation**: Implement rate limiting to prevent brute-force attacks
- **Implementation**: Use a middleware to track requests per IP/user
- **Code Example**:
  ```python
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address
  from slowapi.errors import RateLimitExceeded

  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

  @app.get("/api/secure")
  @limiter.limit("10/minute")
  async def secure_endpoint(request: Request):
      return {"message": "secure"}
  ```

#### API Input Validation
- **Recommendation**: Validate all API inputs using Pydantic models
- **Implementation**: Create strict models for all API inputs
- **Code Example**:
  ```python
  from pydantic import BaseModel, Field, validator
  import re

  class UserCreate(BaseModel):
      username: str = Field(..., min_length=3, max_length=50)
      email: str
      password: str = Field(..., min_length=8)
      
      @validator('username')
      def username_alphanumeric(cls, v):
          if not re.match("^[a-zA-Z0-9_-]+$", v):
              raise ValueError('Username must be alphanumeric')
          return v
          
      @validator('email')
      def email_valid(cls, v):
          if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
              raise ValueError('Invalid email address')
          return v
  ```

### 3. Secrets Management

#### Environment Variable Security
- **Recommendation**: Never hardcode secrets in source code
- **Implementation**: Use environment variables or a dedicated secrets manager
- **Code Example**:
  ```python
  import os
  from typing import Optional

  # Get from environment or raise an error
  API_KEY = os.getenv("API_KEY")
  if not API_KEY:
      raise ValueError("API_KEY environment variable is required")
  ```

#### Rotation of Secrets
- **Recommendation**: Implement a mechanism to rotate secrets without downtime
- **Implementation**: Use a secrets manager that supports rotation
- **Example Implementation**:
  ```python
  import time
  from typing import Dict

  class SecretManager:
      def __init__(self):
          self.secrets: Dict[str, str] = {}
          self.last_rotation: Dict[str, float] = {}
      
      def get_secret(self, key: str) -> Optional[str]:
          # Check if secret needs rotation
          if key in self.last_rotation:
              if time.time() - self.last_rotation[key] > 86400:  # 24 hours
                  self.rotate_secret(key)
          
          return self.secrets.get(key)
      
      def rotate_secret(self, key: str) -> None:
          # In a real implementation, fetch from a secrets manager
          self.secrets[key] = os.getenv(key)
          self.last_rotation[key] = time.time()
  ```

### 4. Web Application Security

#### Content Security Policy (CSP)
- **Recommendation**: Implement a strict Content Security Policy
- **Implementation**: Configure CSP headers with strict rules
- **Example**:
  ```
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; media-src 'self'; frame-src 'none'
  ```

#### XSS Prevention
- **Recommendation**: Properly encode output and implement a strict CSP
- **Implementation**: Use autoescape in templates and proper encoding for API responses
- **Code Example**:
  ```python
  from markupsafe import Markup, escape

  # In API responses
  return {"message": escape(user_input)}
  
  # In HTML templates (Jinja2)
  {{ user_input | e }}
  ```

#### CSRF Protection
- **Recommendation**: Implement CSRF protection for state-changing operations
- **Implementation**: Use CSRF tokens for all POST/PUT/PATCH/DELETE requests
- **Code Example**:
  ```python
  from fastapi import Form, HTTPException, Depends, Request
  from starlette.csrf import generate_csrf_token, validate_csrf_token

  @app.post("/api/data")
  async def create_data(
      request: Request,
      data: DataCreate,
      csrf_token: str = Form(...),
      api_key: str = Depends(verify_api_key)
  ):
      # Validate CSRF token
      if not validate_csrf_token(csrf_token):
          raise HTTPException(status_code=400, detail="Invalid CSRF token")
      
      # Process request
      # ...
  ```

### 5. Infrastructure Security

#### HTTPS Configuration
- **Recommendation**: Always use HTTPS in production
- **Implementation**: Configure web server to redirect HTTP to HTTPS
- **Example (Nginx)**:
  ```nginx
  server {
      listen 80;
      server_name example.com;
      return 301 https://$server_name$request_uri;
  }
  
  server {
      listen 443 ssl;
      server_name example.com;
      
      ssl_certificate /path/to/cert.pem;
      ssl_certificate_key /path/to/key.pem;
      
      # Additional SSL configuration
      ssl_protocols TLSv1.2 TLSv1.3;
      ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
      ssl_prefer_server_ciphers on;
      ssl_session_cache shared:SSL:10m;
      ssl_session_timeout 1d;
      
      # Additional security headers
      add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
      add_header X-Content-Type-Options "nosniff" always;
      add_header X-Frame-Options "DENY" always;
      add_header X-XSS-Protection "1; mode=block" always;
      
      location / {
          proxy_pass http://localhost:8000;
          # Additional proxy configuration
      }
  }
  ```

#### Container Security
- **Recommendation**: Implement container security best practices
- **Implementation**: Use non-root users, minimal images, and security scanning
- **Dockerfile Example**:
  ```dockerfile
  # Use a minimal base image
  FROM python:3.11-slim
  
  # Create non-root user
  RUN useradd --create-home --shell /bin/bash app
  
  # Set working directory
  WORKDIR /app
  
  # Install dependencies
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  
  # Copy application
  COPY . .
  
  # Set proper permissions
  RUN chown -R app:app /app
  USER app
  
  # Run application
  CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

## Security Testing

### Automated Security Testing
- **Implementation**: `backend/security_tests.py`
- **Features**:
  - API authentication testing
  - CORS policy validation
  - Security header verification
  - Input sanitization testing
  - Rate limiting verification
  - SQL injection testing
  - XSS prevention testing

### Running Security Tests
```bash
# Set environment variables
export API_URL="http://localhost:8000"
export API_KEY="your_api_key"

# Run security tests
python backend/security_tests.py
```

## Deployment Security Checklist

- [ ] All secrets are stored in environment variables or a dedicated secrets manager
- [ ] Passwords are hashed with bcrypt or argon2
- [ ] API endpoints require authentication
- [ ] CORS is configured with specific allowed origins
- [ ] Security headers are properly set
- [ ] HTTPS is enforced in production
- [ ] Input validation is implemented for all user inputs
- [ ] Database connections use SSL
- [ ] Database users have minimal required privileges
- [ ] Rate limiting is implemented
- [ ] CSRF protection is enabled for state-changing operations
- [ ] Container runs as non-root user
- [ ] Logging captures security events
- [ ] Security tests pass
- [ ] Error messages don't leak sensitive information
- [ ] API documentation is not exposed in production
- [ ] Dependencies are regularly updated and scanned for vulnerabilities
- [ ] File permissions are properly set for all sensitive files
- [ ] Backups are encrypted
- [ ] Audit logging is implemented for critical operations

## OWASP Top 10 Compliance

The implemented security measures address the following OWASP Top 10 risks:

1. **A01:2021 - Broken Access Control**: Implemented API key authentication and JWT token validation
2. **A02:2021 - Cryptographic Failures**: Implemented secure password hashing and token generation
3. **A03:2021 - Injection**: Implemented input sanitization and parameterized queries
4. **A04:2021 - Insecure Design**: Implemented security headers and middleware for defense in depth
5. **A05:2021 - Security Misconfiguration**: Implemented secure CORS and security headers
6. **A06:2021 - Vulnerable and Outdated Components**: Added dependency security to requirements
7. **A07:2021 - Identification and Authentication Failures**: Implemented secure authentication mechanisms
8. **A08:2021 - Software and Data Integrity Failures**: Recommended supply chain security measures
9. **A09:2021 - Security Logging and Monitoring Failures**: Implemented security logging
10. **A10:2021 - Server-Side Request Forgery**: Recommended SSRF protection measures

## Conclusion

This security hardening guide provides comprehensive measures to secure the MAMcrawler project. By implementing these measures and following the recommendations, the project will be protected against common security threats and comply with industry best practices. Regular security assessments and updates should be conducted to maintain a strong security posture.