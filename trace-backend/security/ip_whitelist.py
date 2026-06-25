import os
import logging
import ipaddress
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Setup a security-specific logger that appends to security.log
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.WARNING)

# Check if handler is already added to prevent duplicate handlers
if not security_logger.handlers:
    fh = logging.FileHandler("security.log", encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] RequestID: %(request_id)s IP: %(ip)s Route: %(route)s -> %(message)s')
    fh.setFormatter(formatter)
    security_logger.addHandler(fh)

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # We only protect /admin/* and /auth/setup-mfa
        path = request.url.path
        if path.startswith("/admin") or path == "/auth/setup-mfa":
            # Extract client IP
            cf_ip = request.headers.get("X-Forwarded-For")
            client_ip = cf_ip.split(",")[0].strip() if cf_ip else request.client.host
            
            # Read whitelist
            whitelist_str = os.getenv("ADMIN_IP_WHITELIST", "")
            whitelisted = False
            
            if whitelist_str:
                ranges = [r.strip() for r in whitelist_str.split(",") if r.strip()]
                # Check client_ip against each range
                try:
                    ip_obj = ipaddress.ip_address(client_ip)
                    for r in ranges:
                        # Handle single IPs or CIDRs
                        network = ipaddress.ip_network(r, strict=False)
                        if ip_obj in network:
                            whitelisted = True
                            break
                except Exception as e:
                    # Logging parsing issue
                    request_id = getattr(request.state, "request_id", "N/A")
                    security_logger.error(
                        f"IP parsing error during whitelist check",
                        extra={"request_id": request_id, "ip": client_ip, "route": path}
                    )
            else:
                # If whitelist is empty, we default to blocking remote requests (only allow localhost)
                if client_ip in ("127.0.0.1", "::1"):
                    whitelisted = True
            
            if not whitelisted:
                request_id = getattr(request.state, "request_id", "N/A")
                # Log blocked attempt
                security_logger.warning(
                    "Blocked unauthorized access to restricted endpoint",
                    extra={"request_id": request_id, "ip": client_ip, "route": path}
                )
                return Response(status_code=403)
                
        return await call_next(request)
