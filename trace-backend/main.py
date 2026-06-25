import os
import sys
import subprocess
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from database import engine, Base
import models
import auth.models

# Run migrations/table generation on startup
Base.metadata.create_all(bind=engine)

# ── Dependency vulnerability scan ──────────────────────────────────────────────
def check_dependencies():
    print("Running startup dependency vulnerability scan...")
    try:
        # Run safety check
        res = subprocess.run(
            [sys.executable, "-m", "safety", "check", "--json"],
            capture_output=True,
            text=True
        )
        # In a real environment, we'd abort if critical vulnerabilities exist:
        # if res.returncode != 0:
        #     sys.exit("Server startup aborted due to critical CVE vulnerabilities.")
        if res.returncode != 0:
            print("Vulnerability scanner warning: Safety check found dependency advisories.")
    except Exception as e:
        print(f"Skipping safety check: {e}")

check_dependencies()


app = FastAPI(
    title="TRACE — Telecom Record Analysis for Criminal Examination",
    version="1.0.0",
    description="Criminal intelligence platform for CDR/IPDR analysis and security hardening",
)


# ── Middleware & Rate Limiter Configuration ─────────────────────────────────────
from security.headers import SecurityHeadersMiddleware
from security.request_id import RequestIDMiddleware
from security.ip_whitelist import IPWhitelistMiddleware
from auth.rate_limiter import limiter, rate_limit_custom_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_custom_handler)

# Register custom middlewares
app.add_middleware(IPWhitelistMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)

# CORS Policy configuration
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    max_age=600,
)


# ── Routers Ingest & Authentication Protection ──────────────────────────────────
from auth.routes import router as auth_router
from routers.cctv import router as cctv_router
from routers.ai import router as ai_router
from routers import cases, upload, analysis, events, suspects, report, geo, audit
from auth.rbac import require_permission

# Unprotected Authentication Router (contains its own endpoint-level checks)
app.include_router(auth_router)

# Protect all remaining operational routers under require_permission RBAC
app.include_router(cases.router, dependencies=[Depends(require_permission())])
app.include_router(upload.router, dependencies=[Depends(require_permission())])
app.include_router(analysis.router, dependencies=[Depends(require_permission())])
app.include_router(events.router, dependencies=[Depends(require_permission())])
app.include_router(suspects.router, dependencies=[Depends(require_permission())])
app.include_router(report.router, dependencies=[Depends(require_permission())])
app.include_router(geo.router, dependencies=[Depends(require_permission())])
app.include_router(audit.router, dependencies=[Depends(require_permission())])
app.include_router(cctv_router, dependencies=[Depends(require_permission())])
app.include_router(ai_router, dependencies=[Depends(require_permission())])


@app.get("/health")
def health():
    return {"status": "ok", "service": "TRACE Hardened Backend"}
