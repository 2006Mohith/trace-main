import os
from fastapi import Request, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session
from database import get_db
from auth.jwt_handler import verify_token
from security.audit_logger import log_audit_enhanced

# Permission map mapping each role to allowed route prefixes / actions
PERMISSIONS = {
    "SP": ["*"],  # Full system access
    "INSPECTOR": ["/cases", "/upload", "/analyze", "/suspects", "/network", "/map", "/cctv", "/events", "/ai"],
    "CONSTABLE": ["/cases:GET", "/suspects:GET", "/cctv/upload"],
    "ADMIN": ["/admin", "/audit", "/officers", "/auth/setup-mfa"]
}

def has_permission(role: str, path: str, method: str) -> bool:
    allowed_list = PERMISSIONS.get(role, [])
    if "*" in allowed_list:
        return True
        
    for pattern in allowed_list:
        if ":" in pattern:
            pat_path, pat_method = pattern.split(":", 1)
            if path.startswith(pat_path) and method.upper() == pat_method.upper():
                return True
        else:
            if path.startswith(pattern):
                return True
    return False

class PermissionChecker:
    def __init__(self, action: str = None):
        self.action = action

    async def __call__(self, request: Request, db: Session = Depends(get_db)):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            if os.getenv("ENVIRONMENT") == "development":
                # Auto-authenticate as SP mock user profile (ADMIN001) in development mode
                from auth.models import Officer
                mock_officer = db.query(Officer).filter(Officer.badge_number == "ADMIN001").first()
                if mock_officer:
                    officer_id = mock_officer.id
                    role = mock_officer.role
                    district = mock_officer.district
                else:
                    officer_id = "mock-admin-uuid-1234"
                    role = "SP"
                    district = "ongole"
                
                jti = "mock-development-jti"
                
                request.state.officer_id = officer_id
                request.state.officer_role = role
                request.state.officer_district = district
                request.state.session_jti = jti
                
                # Check permissions
                path = request.url.path
                method = request.method
                check_path = self.action if self.action else path
                
                if not has_permission(role, check_path, method):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: Insufficient permissions"
                    )
                
                return {
                    "officer_id": officer_id,
                    "role": role,
                    "district": district,
                    "jti": jti
                }

            # Log UNAUTHORIZED_ACCESS
            log_audit_enhanced(
                db=db,
                action_type="UNAUTHORIZED_ACCESS",
                entity_type="API",
                detail={"reason": "Missing or malformed Authorization header"},
                status="FAILURE",
                request=request
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
        token = auth_header.split(" ", 1)[1]
        try:
            payload = verify_token(token)
            officer_id = payload.get("sub")
            role = payload.get("role")
            district = payload.get("district")
            jti = payload.get("jti")
            
            if not officer_id or not role:
                raise JWTError("Invalid payload")
                
            # Attach details to request state for downstream routes and logger
            request.state.officer_id = officer_id
            request.state.officer_role = role
            request.state.officer_district = district
            request.state.session_jti = jti
            
            # Check permissions
            path = request.url.path
            method = request.method
            
            # If a specific action was passed, check that as well
            check_path = self.action if self.action else path
            
            if not has_permission(role, check_path, method):
                # Log UNAUTHORIZED_ACCESS
                log_audit_enhanced(
                    db=db,
                    action_type="UNAUTHORIZED_ACCESS",
                    entity_type="API",
                    entity_id=officer_id,
                    entity_label=f"Officer ID {officer_id}",
                    detail={"reason": f"Role {role} unauthorized for {method} {path}"},
                    status="FAILURE",
                    request=request
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Insufficient permissions"
                )
                
            return {
                "officer_id": officer_id,
                "role": role,
                "district": district,
                "jti": jti
            }
            
        except JWTError as e:
            log_audit_enhanced(
                db=db,
                action_type="UNAUTHORIZED_ACCESS",
                entity_type="API",
                detail={"reason": f"Token verification failed: {e}"},
                status="FAILURE",
                request=request
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired credentials: {e}",
                headers={"WWW-Authenticate": "Bearer"}
            )

# Dependency wrapper
def require_permission(action: str = None):
    return PermissionChecker(action)
