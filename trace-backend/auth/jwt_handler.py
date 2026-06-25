import os
import uuid
from datetime import datetime, timedelta
from jose import jwt, JWTError
import redis

# Loaded from environment
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_123456789_placeholder")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", "dev_refresh_secret_key_123456789_placeholder")
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 10
REFRESH_TOKEN_EXPIRE_HOURS = 8

# Initialize Redis client with fallback
redis_client = None
in_memory_revoked = {}  # Fallback dict: jti -> expiration timestamp
in_memory_sessions = {} # Fallback dict: jti -> metadata dict

try:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url, socket_timeout=2.0)
    # Ping test
    redis_client.ping()
except Exception:
    print("Warning: Redis not available. Falling back to in-memory session and revocation cache.")
    redis_client = None

def create_access_token(officer_id: str, role: str, district: str) -> str:
    jti = str(uuid.uuid4())
    now = datetime.utcnow()
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": officer_id,
        "role": role,
        "district": district,
        "jti": jti,
        "iat": now,
        "exp": expire
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    # Store session metadata in Redis / memory
    track_session(jti, officer_id)
    return token

def create_refresh_token(officer_id: str) -> str:
    jti = str(uuid.uuid4())
    now = datetime.utcnow()
    expire = now + timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)
    
    payload = {
        "sub": officer_id,
        "jti": jti,
        "iat": now,
        "exp": expire
    }
    
    token = jwt.encode(payload, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_token(token: str, is_refresh: bool = False) -> dict:
    key = REFRESH_SECRET_KEY if is_refresh else SECRET_KEY
    try:
        payload = jwt.decode(token, key, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        
        # Check if jti is revoked
        if jti and is_revoked(jti):
            raise JWTError("Token has been revoked")
            
        # Check session inactivity limit for access tokens
        if not is_refresh and jti:
            if not update_session_activity(jti):
                raise JWTError("Session expired due to inactivity")
                
        return payload
    except JWTError as e:
        raise e

def revoke_token(jti: str, exp_timestamp: int):
    # Store revoked JTI with TTL matching token expiry
    ttl = int(exp_timestamp - datetime.utcnow().timestamp())
    if ttl <= 0:
        return
        
    if redis_client:
        try:
            redis_client.setex(f"revoked:{jti}", ttl, "1")
        except Exception:
            in_memory_revoked[jti] = exp_timestamp
    else:
        in_memory_revoked[jti] = exp_timestamp

def is_revoked(jti: str) -> bool:
    if redis_client:
        try:
            val = redis_client.get(f"revoked:{jti}")
            return val is not None
        except Exception:
            pass
            
    # Check in-memory database fallback
    exp = in_memory_revoked.get(jti)
    if exp:
        if datetime.utcnow().timestamp() > exp:
            # Clean up expired revoked token
            del in_memory_revoked[jti]
            return False
        return True
    return False

def track_session(jti: str, officer_id: str, ip: str = "N/A", user_agent: str = "N/A"):
    # Store session details in Redis/in-memory with 10-minute inactivity TTL
    metadata = {
        "officer_id": officer_id,
        "ip": ip,
        "user_agent": user_agent,
        "login_time": datetime.utcnow().isoformat() + "Z",
        "last_active": datetime.utcnow().timestamp()
    }
    ttl = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    if redis_client:
        try:
            redis_client.setex(f"session:{jti}", ttl, json.dumps(metadata))
        except Exception:
            in_memory_sessions[jti] = metadata
    else:
        in_memory_sessions[jti] = metadata

def update_session_activity(jti: str) -> bool:
    """Updates the last_active time. Returns False if the session has expired."""
    now = datetime.utcnow().timestamp()
    ttl = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    if redis_client:
        try:
            sess_data = redis_client.get(f"session:{jti}")
            if not sess_data:
                return False
            import json
            sess = json.loads(sess_data)
            # Check gap (10 minutes inactivity)
            if now - sess.get("last_active", 0) > ttl:
                revoke_token(jti, int(now + ttl))
                redis_client.delete(f"session:{jti}")
                return False
            sess["last_active"] = now
            redis_client.setex(f"session:{jti}", ttl, json.dumps(sess))
            return True
        except Exception:
            pass
            
    # Fallback in-memory session tracking
    sess = in_memory_sessions.get(jti)
    if not sess:
        return False
    if now - sess.get("last_active", 0) > ttl:
        revoke_token(jti, int(now + ttl))
        if jti in in_memory_sessions:
            del in_memory_sessions[jti]
        return False
    sess["last_active"] = now
    return True
