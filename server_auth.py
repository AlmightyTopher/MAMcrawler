import secrets
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials, APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED
from config_system import get_secret, set_secret, get_config_value

logger = logging.getLogger("ServerAuth")

security_basic = HTTPBasic(auto_error=False)
security_api_key = APIKeyHeader(name="X-API-Key", auto_error=False)

# Constants for defaults
DEFAULT_USER = "admin"

def get_or_create_admin_credentials():
    """Ensure admin password and API key exist in secrets."""
    # 1. API Key
    try:
        api_key = get_secret("server_api_key")
    except Exception:
        api_key = None
        
    if not api_key:
        api_key = secrets.token_urlsafe(32)
        try:
            set_secret("server_api_key", api_key)
            logger.info("Generated new Server API Key")
        except Exception as e:
            logger.warning(f"Could not persist API key: {e}")

    # 2. Admin Password
    try:
        password = get_secret("server_admin_password")
    except Exception:
        password = None
        
    if not password:
        password = secrets.token_urlsafe(16)
        try:
            set_secret("server_admin_password", password)
            logger.info("Generated new Admin Password")
        except Exception as e:
            logger.warning(f"Could not persist Admin password: {e}")
            
    return api_key, password

# Initialize credentials on module load
SERVER_API_KEY, SERVER_ADMIN_PASSWORD = get_or_create_admin_credentials()

async def get_current_user(
    request: Request,
    api_key_header: Optional[str] = Depends(security_api_key),
    basic_creds: Optional[HTTPBasicCredentials] = Depends(security_basic)
):
    """
    Authenticate request via API Key or Basic Auth.
    Returns "admin" if successful, or raises 401.
    """
    # 1. Check API Key
    if api_key_header:
        # Constant time comparison to prevent timing attacks
        if secrets.compare_digest(api_key_header, SERVER_API_KEY):
            return "admin"
            
    # 2. Check Basic Auth (for browsers)
    if basic_creds:
        # Validate username
        if basic_creds.username != DEFAULT_USER:
            # Fake compare to prevent timing checks on username existence
            secrets.compare_digest(basic_creds.password, "invalid")
        else:
            if secrets.compare_digest(basic_creds.password, SERVER_ADMIN_PASSWORD):
                return "admin"
    
    # 3. Unauthorized
    # If it was a browser request (no API key), return Basic Auth challenge
    headers = {}
    if not api_key_header:
        headers["WWW-Authenticate"] = "Basic"
        
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers=headers
    )

def print_credentials():
    """Helper to print credentials to console on startup (securely)."""
    print("\n" + "="*50)
    print("SECURE ACCESS CREDENTIALS")
    print("="*50)
    print(f"Username: {DEFAULT_USER}")
    print(f"Password: {SERVER_ADMIN_PASSWORD}")
    print(f"API Key:  {SERVER_API_KEY}")
    print("="*50 + "\n")
