import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from database import get_db
from auth.models import Officer
from auth.jwt_handler import (
    create_access_token, create_refresh_token, verify_token, revoke_token,
    SECRET_KEY, ALGORITHM, in_memory_sessions
)
from auth.mfa import verify_totp, generate_totp_secret, generate_backup_codes
from auth.rbac import require_permission
from security.audit_logger import log_audit_enhanced
from auth.rate_limiter import limiter

# Password Hashing using raw bcrypt for Python 3.13 compatibility
import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")



router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    badge_number: str
    password: str

class VerifyOtpRequest(BaseModel):
    challenge_token: str
    code: str  # Can be 6-digit OTP or 8-character backup code

class RefreshRequest(BaseModel):
    refresh_token: str

class SetupMfaRequest(BaseModel):
    badge_number: str


# ── API Endpoints ──────────────────────────────────────────────────────────────

@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    badge = payload.badge_number.strip()
    officer = db.query(Officer).filter(Officer.badge_number == badge).first()
    
    # 1. Check if officer exists and is active
    if not officer or not officer.is_active:
        log_audit_enhanced(db, "LOGIN_FAILURE", "Officer", detail={"badge_number": badge, "reason": "Invalid badge or inactive"}, status="FAILURE", request=request)
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    # 2. Check if account is locked
    if officer.locked_until and officer.locked_until > datetime.utcnow():
        log_audit_enhanced(db, "LOGIN_FAILURE", "Officer", entity_id=officer.id, entity_label=badge, detail={"reason": "Account locked"}, status="FAILURE", request=request)
        raise HTTPException(
            status_code=403, 
            detail=f"Account is temporarily locked. Please try again after {officer.locked_until.isoformat()} UTC."
        )
        
    # 3. Verify password
    if not verify_password(payload.password, officer.hashed_password):
        # Increment failed attempts
        officer.failed_attempts += 1
        if officer.failed_attempts >= 5:
            officer.locked_until = datetime.utcnow() + timedelta(minutes=30)
            log_audit_enhanced(db, "ACCOUNT_LOCKOUT", "Officer", entity_id=officer.id, entity_label=badge, detail={"failed_attempts": officer.failed_attempts}, status="FAILURE", request=request)
        else:
            db.commit()
            
        log_audit_enhanced(db, "LOGIN_FAILURE", "Officer", entity_id=officer.id, entity_label=badge, detail={"reason": "Invalid password", "failed_attempts": officer.failed_attempts}, status="FAILURE", request=request)
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    # Valid password: create short-lived MFA challenge token
    challenge_jti = str(uuid.uuid4()) if 'uuid' in globals() else str(datetime.utcnow().timestamp())
    challenge_exp = datetime.utcnow() + timedelta(minutes=5)
    challenge_payload = {
        "sub": officer.id,
        "badge_number": officer.badge_number,
        "type": "mfa_challenge",
        "jti": challenge_jti,
        "exp": challenge_exp
    }
    
    challenge_token = jwt.encode(challenge_payload, SECRET_KEY, algorithm=ALGORITHM)
    
    # Check if MFA secret is already configured
    has_mfa = officer.totp_secret is not None
    
    log_audit_enhanced(
        db, 
        "LOGIN_CHALLENGE", 
        "Officer", 
        entity_id=officer.id, 
        entity_label=badge, 
        detail={"mfa_configured": has_mfa},
        request=request
    )
    
    return {
        "mfa_required": has_mfa,
        "mfa_setup_required": not has_mfa,
        "challenge_token": challenge_token
    }


@router.post("/verify-otp")
@limiter.limit("3/minute")
def verify_otp(request: Request, payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    # 1. Decode and verify challenge token
    try:
        challenge = jwt.decode(payload.challenge_token, SECRET_KEY, algorithms=[ALGORITHM])
        if challenge.get("type") != "mfa_challenge":
            raise JWTError("Invalid token type")
        officer_id = challenge.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired challenge token")
        
    officer = db.query(Officer).filter(Officer.id == officer_id).first()
    if not officer or not officer.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if officer.locked_until and officer.locked_until > datetime.utcnow():
        raise HTTPException(status_code=403, detail="Account is temporarily locked")
        
    code = payload.code.strip()
    
    # 2. Check TOTP or Backup code
    mfa_success = False
    is_backup_code = len(code) == 8 and not code.isdigit()
    
    if is_backup_code:
        # Check backup codes
        if officer.backup_codes:
            codes_list = [c.strip() for c in officer.backup_codes.split(",") if c.strip()]
            if code in codes_list:
                mfa_success = True
                # Remove consumed backup code
                codes_list.remove(code)
                officer.backup_codes = ",".join(codes_list) if codes_list else None
    else:
        # Check standard TOTP OTP
        if officer.totp_secret:
            mfa_success = verify_totp(officer.totp_secret, code)
            
    if not mfa_success:
        officer.failed_attempts += 1
        if officer.failed_attempts >= 5:
            officer.locked_until = datetime.utcnow() + timedelta(minutes=30)
            log_audit_enhanced(db, "ACCOUNT_LOCKOUT", "Officer", entity_id=officer.id, entity_label=officer.badge_number, detail={"reason": "MFA limit lock"}, status="FAILURE", request=request)
        else:
            db.commit()
            
        log_audit_enhanced(
            db, 
            "OTP_FAILURE", 
            "Officer", 
            entity_id=officer.id, 
            entity_label=officer.badge_number, 
            detail={"is_backup_code": is_backup_code, "failed_attempts": officer.failed_attempts}, 
            status="FAILURE", 
            request=request
        )
        raise HTTPException(status_code=401, detail="Invalid OTP code")
        
    # Reset lockouts on success
    officer.failed_attempts = 0
    officer.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token = create_access_token(officer.id, officer.role, officer.district)
    refresh_token = create_refresh_token(officer.id)
    
    log_audit_enhanced(
        db, 
        "OTP_SUCCESS", 
        "Officer", 
        entity_id=officer.id, 
        entity_label=officer.badge_number, 
        detail={"method": "backup_code" if is_backup_code else "totp"},
        request=request
    )
    
    log_audit_enhanced(
        db, 
        "LOGIN_SUCCESS", 
        "Officer", 
        entity_id=officer.id, 
        entity_label=officer.badge_number,
        request=request
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": officer.role,
        "district": officer.district
    }


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        refresh_payload = verify_token(payload.refresh_token, is_refresh=True)
        officer_id = refresh_payload.get("sub")
        old_jti = refresh_payload.get("jti")
        exp = refresh_payload.get("exp")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired refresh token: {e}")
        
    officer = db.query(Officer).filter(Officer.id == officer_id).first()
    if not officer or not officer.is_active:
        raise HTTPException(status_code=401, detail="Inactive officer")
        
    # Revoke old refresh token JTI
    if old_jti and exp:
        revoke_token(old_jti, exp)
        
    # Generate new tokens
    access_token = create_access_token(officer.id, officer.role, officer.district)
    new_refresh_token = create_refresh_token(officer.id)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(request: Request, current_officer: dict = Depends(require_permission()), db: Session = Depends(get_db)):
    jti = getattr(request.state, "session_jti", None)
    officer_id = current_officer.get("officer_id")
    
    if jti:
        # Revoke access token JTI
        exp_time = datetime.utcnow().timestamp() + (10 * 60)
        revoke_token(jti, exp_time)
        
        # Clean up session state
        if jti in in_memory_sessions:
            del in_memory_sessions[jti]
            
    officer = db.query(Officer).filter(Officer.id == officer_id).first()
    badge = officer.badge_number if officer else "UNKNOWN"
    
    log_audit_enhanced(
        db, 
        "LOGOUT", 
        "Officer", 
        entity_id=officer_id, 
        entity_label=badge,
        request=request
    )
    return {"status": "ok", "message": "Successfully logged out"}


@router.post("/setup-mfa")
def setup_mfa(payload: SetupMfaRequest, current_officer: dict = Depends(require_permission()), db: Session = Depends(get_db)):
    # Admin check
    if current_officer.get("role") != "ADMIN" and current_officer.get("role") != "SP":
        raise HTTPException(status_code=403, detail="Only Admins or SPs can register MFA credentials for officers")
        
    officer = db.query(Officer).filter(Officer.badge_number == payload.badge_number.strip()).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
        
    # Generate TOTP secret and backup codes
    secret = generate_totp_secret()
    backup_codes = generate_backup_codes()
    
    officer.totp_secret = secret
    officer.backup_codes = ",".join(backup_codes)
    db.commit()
    
    provisioning_uri = f"otpauth://totp/TRACE:{officer.badge_number}?secret={secret}&issuer=TRACE"
    
    log_audit_enhanced(
        db, 
        "MFA_SETUP", 
        "Officer", 
        entity_id=officer.id, 
        entity_label=officer.badge_number, 
        detail={"triggered_by": current_officer.get("officer_id")}
    )
    
    return {
        "badge_number": officer.badge_number,
        "totp_secret": secret,
        "provisioning_uri": provisioning_uri,
        "backup_codes": backup_codes
    }


@router.get("/me")
def get_me(current_officer: dict = Depends(require_permission()), db: Session = Depends(get_db)):
    officer_id = current_officer.get("officer_id")
    officer = db.query(Officer).filter(Officer.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer profile not found")
        
    return {
        "id": officer.id,
        "badge_number": officer.badge_number,
        "role": officer.role,
        "district": officer.district,
        "is_active": officer.is_active,
        "last_login": officer.last_login.isoformat() + "Z" if officer.last_login else None,
        "created_at": officer.created_at.isoformat() + "Z"
    }
