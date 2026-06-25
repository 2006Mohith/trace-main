import io
import os
import uuid
import logging
from datetime import datetime

logger = logging.getLogger("cctv_router")
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import CCTVCamera, CCTVFaceEntry, CCTVSighting, Suspect
from auth.rbac import require_permission
from engines.cctv_engine import (
    register_suspect_face, match_face_against_registry,
    process_video_for_surveillance, check_liveness
)
from engines.cctv_config import MAX_VIDEO_SIZE_MB
from security.audit_logger import log_audit_enhanced
from security.input_sanitizer import validate_file_upload, validate_coordinates, sanitize_text
from security.encryption import hash_file

router = APIRouter(prefix="/cctv", tags=["cctv"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CameraCreate(BaseModel):
    camera_id: str = Field(..., example="ONG-CAM-01")
    location_name: str = Field(..., example="Ongole Junction Main Road")
    latitude: float
    longitude: float
    rtsp_url: str = Field(..., example="rtsp://admin:pass@192.168.1.100:554/stream1")

class CameraStatusUpdate(BaseModel):
    status: str = Field(..., example="MAINTENANCE")  # ONLINE | OFFLINE | MAINTENANCE

class SightingVerifyRequest(BaseModel):
    verified: bool
    officer_note: Optional[str] = None

class SightingResponse(BaseModel):
    id: str
    camera_id: str
    location_name: str
    suspect_id: Optional[str]
    suspect_label: Optional[str]
    captured_at: str
    confidence_score: float
    match_category: Optional[str]
    is_verified: bool
    frame_path: str
    is_live: bool
    model_used: Optional[str]
    liveness_score: Optional[float]


# ── Helpers ───────────────────────────────────────────────────────────────────

def validate_media_type_by_magic_bytes(content: bytes) -> str:
    """Validates file format using magic signature bytes instead of extension."""
    if len(content) < 8:
        return "UNKNOWN"
    
    # JPEG check
    if content[0:3] == b"\xff\xd8\xff":
        return "JPEG"
    
    # PNG check
    if content[0:4] == b"\x89PNG":
        return "PNG"
        
    # MP4 check (bytes 4-7 are 'ftyp')
    if content[4:8] == b"ftyp":
        return "MP4"
        
    # AVI check (first 4 bytes RIFF, bytes 8-11 are 'AVI ')
    if content[0:4] == b"RIFF":
        return "AVI"
            
    return "UNKNOWN"


# ── API Endpoints ──────────────────────────────────────────────────────────────

@router.post("/register-face/{suspect_id}", status_code=status.HTTP_201_CREATED)
async def register_face(
    suspect_id: str,
    request: Request,
    file: UploadFile = File(...),
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    # Check if suspect exists
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
        
    content = await file.read()
    
    # 1. Validate file
    media_type = validate_media_type_by_magic_bytes(content)
    if media_type not in ("JPEG", "PNG"):
        raise HTTPException(status_code=415, detail="Unsupported Media Type. Face registration only supports JPEG or PNG formats.")
        
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size exceeds maximum 10MB limit.")
        
    # 2. Ingest Reference Face
    try:
        res = register_suspect_face(suspect_id, content, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal face registration error: {e}")
        
    log_audit_enhanced(
        db=db,
        action_type="FACE_REGISTER",
        entity_type="Suspect",
        entity_id=suspect_id,
        entity_label=suspect.label,
        detail={"face_id": res["face_id"], "quality_score": res["quality_score"], "image_hash": res["image_hash"]},
        request=request
    )
    
    return res


@router.delete("/face/{suspect_id}/{face_id}")
async def delete_face(
    suspect_id: str,
    face_id: str,
    request: Request,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    # Check if suspect exists
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
        
    entry = db.query(CCTVFaceEntry).filter(
        CCTVFaceEntry.suspect_id == suspect_id,
        CCTVFaceEntry.face_id == face_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Reference face not found")
        
    # Remove files from disk
    if os.path.exists(entry.image_path):
        os.remove(entry.image_path)
    if os.path.exists(entry.embedding_path):
        os.remove(entry.embedding_path)
        
    # Delete from DB
    db.delete(entry)
    db.commit()
    
    # Remove from memory caches
    from engines.cctv_engine import EMBEDDING_CACHE, PHASH_CACHE
    if face_id in EMBEDDING_CACHE["ArcFace"]:
        del EMBEDDING_CACHE["ArcFace"][face_id]
    cache_key = f"{face_id}_facenet"
    if cache_key in EMBEDDING_CACHE["Facenet512"]:
        del EMBEDDING_CACHE["Facenet512"][cache_key]
    if face_id in PHASH_CACHE:
        del PHASH_CACHE[face_id]
        
    log_audit_enhanced(
        db=db,
        action_type="FACE_DELETE",
        entity_type="Suspect",
        entity_id=suspect_id,
        entity_label=suspect.label,
        detail={"face_id": face_id},
        request=request
    )
    return {"status": "ok", "message": "Reference face deleted successfully"}


@router.post("/match")
async def match(
    request: Request,
    file: UploadFile = File(...),
    sample_rate: int = Form(15),
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    # Ensure default virtual cameras exist to satisfy foreign key constraints
    for default_cam_id, name in [("UPLOAD-IMAGE", "Uploaded Image Analysis"), ("UPLOAD-VIDEO", "Uploaded Video Analysis")]:
        cam = db.query(CCTVCamera).filter(CCTVCamera.camera_id == default_cam_id).first()
        if not cam:
            try:
                new_cam = CCTVCamera(
                    camera_id=default_cam_id,
                    location_name=name,
                    latitude=0.0,
                    longitude=0.0,
                    status="ONLINE"
                )
                db.add(new_cam)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to create default camera {default_cam_id}: {e}")

    content = await file.read()
    
    # 1. Validate file
    media_type = validate_media_type_by_magic_bytes(content)
    if media_type == "UNKNOWN":
        raise HTTPException(status_code=415, detail="Unsupported Media Type. Supported formats are JPEG, PNG, MP4, or AVI.")
        
    if len(content) > MAX_VIDEO_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds maximum size of {MAX_VIDEO_SIZE_MB}MB.")
        
    file_hash = hash_file(content)
    
    # Save original file to storage/cctv_uploads/{YYYYMMDD}/{request_id}_{original_filename}
    date_str = datetime.utcnow().strftime("%Y%m%d")
    upload_dir = os.path.join("storage", "cctv_uploads", date_str)
    os.makedirs(upload_dir, exist_ok=True)
    
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    original_filename = file.filename or "uploaded_file"
    clean_filename = "".join(c for c in original_filename if c.isalnum() or c in (".", "_", "-"))
    dest_filename = f"{request_id}_{clean_filename}"
    dest_path = os.path.join(upload_dir, dest_filename)
    
    with open(dest_path, "wb") as f:
        f.write(content)
        
    if media_type in ("MP4", "AVI"):
        try:
            res = process_video_for_surveillance(
                video_bytes=content,
                camera_id="UPLOAD-VIDEO",
                db=db,
                sample_every_n_frames=sample_rate
            )
            log_audit_enhanced(
                db=db,
                action_type="FACE_MATCH",
                entity_type="Video",
                entity_label=file.filename,
                detail={"file_hash": file_hash, "matches_found": res["unique_sightings"]},
                request=request
            )
            return res
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Video surveillance match process failed: {e}")
            
    else:
        # Run match against registry
        try:
            res = match_face_against_registry(content, db)
            
            # Save all confirmed/probable sightings as CCTVSighting records
            for match_res in res["results"]:
                if match_res["match_found"] and match_res["match_confidence"] in ("CONFIRMED", "PROBABLE"):
                    sighting = CCTVSighting(
                        camera_id="UPLOAD-IMAGE",
                        suspect_id=match_res["suspect_id"],
                        captured_at=datetime.utcnow(),
                        confidence_score=match_res["confidence_percent"],
                        match_category=match_res["match_confidence"],
                        image_hash=file_hash,
                        frame_path=dest_path,
                        is_live=match_res["is_live"],
                        is_verified=False,
                        model_used=match_res["model_used"],
                        liveness_score=match_res["liveness_score"]
                    )
                    db.add(sighting)
            db.commit()
            
            log_audit_enhanced(
                db=db,
                action_type="FACE_MATCH",
                entity_type="Image",
                entity_label=file.filename,
                detail={"file_hash": file_hash, "results": res["results"]},
                request=request
            )
            return res
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image match process failed: {e}")


@router.post("/cameras", status_code=status.HTTP_201_CREATED)
def register_camera(
    payload: CameraCreate,
    request: Request,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    loc_sanitized = sanitize_text(payload.location_name)
    cam_id_sanitized = sanitize_text(payload.camera_id)
    
    if not validate_coordinates(payload.latitude, payload.longitude):
        raise HTTPException(status_code=422, detail="Invalid GPS coordinates")
        
    existing = db.query(CCTVCamera).filter(CCTVCamera.camera_id == cam_id_sanitized).first()
    if existing:
        raise HTTPException(status_code=409, detail="Camera ID already exists")
        
    camera = CCTVCamera(
        camera_id=cam_id_sanitized,
        location_name=loc_sanitized,
        latitude=payload.latitude,
        longitude=payload.longitude,
        rtsp_url=payload.rtsp_url, # Encrypted automatically
        status="ONLINE"
    )
    
    db.add(camera)
    db.commit()
    db.refresh(camera)
    
    log_audit_enhanced(
        db=db,
        action_type="CAMERA_REGISTER",
        entity_type="Camera",
        entity_id=camera.id,
        entity_label=camera.camera_id,
        request=request
    )
    
    return {"status": "ok", "camera_id": camera.camera_id}


@router.get("/cameras")
def get_cameras(
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    cameras = db.query(CCTVCamera).all()
    return [
        {
            "id": c.id,
            "camera_id": c.camera_id,
            "location_name": c.location_name,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "status": c.status,
            "last_ping": c.last_ping.isoformat() + "Z"
        }
        for c in cameras
    ]


@router.patch("/cameras/{camera_id}/status")
def update_camera_status(
    camera_id: str,
    payload: CameraStatusUpdate,
    request: Request,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    camera = db.query(CCTVCamera).filter(CCTVCamera.camera_id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    status_sanit = sanitize_text(payload.status).upper()
    if status_sanit not in {"ONLINE", "OFFLINE", "MAINTENANCE"}:
        raise HTTPException(status_code=422, detail="Invalid status value")
        
    camera.status = status_sanit
    camera.last_ping = datetime.utcnow()
    db.commit()
    
    log_audit_enhanced(
        db=db,
        action_type="CAMERA_STATUS_UPDATE",
        entity_type="Camera",
        entity_id=camera.id,
        entity_label=camera.camera_id,
        detail={"status": status_sanit},
        request=request
    )
    
    return {"status": "ok", "camera_id": camera.camera_id, "new_status": camera.status}


@router.get("/sightings/{suspect_id}", response_model=List[SightingResponse])
def get_sightings(
    suspect_id: str,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    # Verify suspect exists
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
        
    sightings = db.query(CCTVSighting).filter(CCTVSighting.suspect_id == suspect_id).order_by(CCTVSighting.captured_at.desc()).all()
    
    results = []
    for s in sightings:
        camera = db.query(CCTVCamera).filter(CCTVCamera.camera_id == s.camera_id).first()
        location_name = camera.location_name if camera else "Uploaded Media"
        
        results.append(SightingResponse(
            id=s.id,
            camera_id=s.camera_id,
            location_name=location_name,
            suspect_id=s.suspect_id,
            suspect_label=suspect.label,
            captured_at=s.captured_at.isoformat() + "Z",
            confidence_score=s.confidence_score,
            match_category=s.match_category,
            is_verified=s.is_verified,
            frame_path=s.frame_path,
            is_live=s.is_live,
            model_used=s.model_used,
            liveness_score=s.liveness_score
        ))
    return results


@router.get("/sightings/recent", response_model=List[SightingResponse])
def get_recent_sightings(
    limit: int = 50,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    sightings = db.query(CCTVSighting).order_by(CCTVSighting.captured_at.desc()).limit(limit).all()
    
    results = []
    for s in sightings:
        suspect_label = "Unknown Suspect"
        if s.suspect_id:
            sus = db.query(Suspect).filter(Suspect.id == s.suspect_id).first()
            if sus:
                suspect_label = sus.label
                
        camera = db.query(CCTVCamera).filter(CCTVCamera.camera_id == s.camera_id).first()
        location_name = camera.location_name if camera else "Uploaded Media"
        
        results.append(SightingResponse(
            id=s.id,
            camera_id=s.camera_id,
            location_name=location_name,
            suspect_id=s.suspect_id,
            suspect_label=suspect_label,
            captured_at=s.captured_at.isoformat() + "Z",
            confidence_score=s.confidence_score,
            match_category=s.match_category,
            is_verified=s.is_verified,
            frame_path=s.frame_path,
            is_live=s.is_live,
            model_used=s.model_used,
            liveness_score=s.liveness_score
        ))
    return results


@router.post("/sightings/{sighting_id}/verify")
def verify_sighting(
    sighting_id: str,
    payload: SightingVerifyRequest,
    request: Request,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    sighting = db.query(CCTVSighting).filter(CCTVSighting.id == sighting_id).first()
    if not sighting:
        raise HTTPException(status_code=404, detail="Sighting not found")
        
    sighting.is_verified = payload.verified
    sighting.verified_by = current_officer.get("officer_id")
    db.commit()
    
    sus = db.query(Suspect).filter(Suspect.id == sighting.suspect_id).first() if sighting.suspect_id else None
    lbl = sus.label if sus else "Unknown"
    
    log_audit_enhanced(
        db=db,
        action_type="SIGHTING_VERIFIED",
        entity_type="Sighting",
        entity_id=sighting.id,
        entity_label=f"Suspect {lbl} at camera {sighting.camera_id}",
        detail={"verified": payload.verified, "officer_note": payload.officer_note},
        request=request
    )
    
    return {"status": "ok", "sighting_id": sighting.id, "is_verified": sighting.is_verified}


@router.get("/suspect/{suspect_id}/face-quality")
def get_suspect_face_quality(
    suspect_id: str,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
        
    entries = db.query(CCTVFaceEntry).filter(CCTVFaceEntry.suspect_id == suspect_id).all()
    
    return [
        {
            "face_id": entry.face_id,
            "quality_score": entry.quality_score,
            "needs_replacement": entry.quality_score < 60,
            "registered_at": entry.registered_at.isoformat() + "Z"
        }
        for entry in entries
    ]
