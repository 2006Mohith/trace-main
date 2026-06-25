import os
from fastapi import Request, Response, HTTPException
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

# Custom key function that targets officer ID if logged in, falling back to remote IP
def get_officer_or_ip_identifier(request: Request) -> str:
    if hasattr(request.state, "officer_id") and request.state.officer_id:
        return f"officer:{request.state.officer_id}"
    
    # Fallback to IP address
    cf_ip = request.headers.get("x-forwarded-for")
    return cf_ip.split(",")[0].strip() if cf_ip else (request.client.host if request.client else "127.0.0.1")

limiter = Limiter(key_func=get_officer_or_ip_identifier)

# Custom exception handler to return 429 with Retry-After header
def rate_limit_custom_handler(request: Request, exc: RateLimitExceeded) -> Response:
    retry_after = "60"  # Default fallback
    if hasattr(exc, "retry_after") and exc.retry_after:
        retry_after = str(exc.retry_after)
    elif "Retry-After" in exc.headers:
        retry_after = exc.headers["Retry-After"]
        
    response = JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."}
    )
    response.headers["Retry-After"] = retry_after
    
    # Optional: Log rate limit hit
    # Note: we will log audit events where needed
    return response
