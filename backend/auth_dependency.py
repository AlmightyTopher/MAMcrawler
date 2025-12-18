import secrets
import logging
import os
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials, APIKeyHeader
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

security_api_key = APIKeyHeader(name="X-API-Key", auto_error=False)
security_basic = HTTPBasic(auto_error=False)

# Global fallback for generated key if not in env
GENERATED_API_KEY = None

def get_effective_api_key():
    global GENERATED_API_KEY
    if settings.API_KEY:
        return settings.API_KEY
    
    if not GENERATED_API_KEY:
        GENERATED_API_KEY = secrets.token_urlsafe(32)
        logger.warning("No API_KEY set in configuration. Generated temporary key: %s", GENERATED_API_KEY)
        print(f"\n[SECURITY] Generated Temporary API Key: {GENERATED_API_KEY}\n")
        
    return GENERATED_API_KEY

async def get_authorized_user(
    request: Request,
    api_key_header: str | None = Depends(security_api_key),
    basic_creds: HTTPBasicCredentials | None = Depends(security_basic)
):
    effective_key = get_effective_api_key()
    
    # 1. Check API Key Header
    if api_key_header:
        if secrets.compare_digest(api_key_header, effective_key):
            return "admin"
            
    # 2. Check Basic Auth (User=admin, Pass=API_KEY)
    if basic_creds:
        # Use constant time everywhere
        username_correct = secrets.compare_digest(basic_creds.username, "admin")
        password_correct = secrets.compare_digest(basic_creds.password, effective_key)
        
        if username_correct and password_correct:
            return "admin"

    # 3. Unauthorized
    headers = {}
    if not api_key_header:
         headers["WWW-Authenticate"] = "Basic"
         
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized access",
        headers=headers
    )
