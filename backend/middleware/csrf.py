from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("CSRF")

async def csrf_protection_middleware(request: Request, call_next):
    """
    Middleware to prevent CSRF attacks.
    Enforces that all state-changing requests (POST, PUT, DELETE, PATCH)
    must contain either:
    1. A valid X-API-Key header (script/program access)
    2. A custom X-MAM-Client header (browser dashboard access)
    
    Standard HTML forms cannot send custom headers, and cross-origin fetch
    requests with custom headers trigger a CORS Preflight, which we control.
    """
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        # Allow if API Key is present (assumed to be non-browser script)
        if request.headers.get("X-API-Key"):
            return await call_next(request)
            
        # Allow if Custom Client Header is present (Dashboard)
        # Browsers can only send this if Same-Origin or CORS-Approved
        if request.headers.get("X-MAM-Client"):
            return await call_next(request)
            
        logger.warning(f"Blocked potential CSRF request to {request.url.path} from {request.client.host}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "CSRF Protection: Missing X-MAM-Client header or X-API-Key"}
        )
        
    return await call_next(request)
