import os
import io
import uuid
import base64
import logging
import hashlib
from datetime import datetime
from typing import List, Optional, Dict
import numpy as np
import cv2
from PIL import Image, ImageOps
import imagehash
from skimage.feature import local_binary_pattern
from sqlalchemy.orm import Session

# Import Config Constants
from engines.cctv_config import (
    MIN_FACE_SIZE,
    MIN_MTCNN_CONFIDENCE,
    MIN_FACE_AREA_RATIO,
    ARCFACE_THRESHOLD,
    CONFIRMED_THRESHOLD,
    PROBABLE_THRESHOLD,
    FALLBACK_MODEL,
    EMBEDDING_CACHE_SIZE,
    MIN_BLUR_SCORE,
    MAX_MOIRE_SCORE,
    MAX_LBP_DISTANCE,
    DEFAULT_SAMPLE_RATE,
    MIN_SIGHTING_FRAMES,
    MAX_VIDEO_SIZE_MB,
    THUMBNAIL_WIDTH,
    MIN_REGISTRY_QUALITY,
    REJECT_REGISTRY_QUALITY
)

from models import CCTVCamera, CCTVFaceEntry, CCTVSighting, Suspect

logger = logging.getLogger("cctv_engine")

# Lazy-loaded detectors and models
_deepface_module = None
_mtcnn_module = None

# Global In-Memory Caches to avoid disk reads/re-extraction
# Key: face_id, Value: numpy array/ImageHash
EMBEDDING_CACHE = {
    "ArcFace": {},
    "Facenet512": {}
}
PHASH_CACHE = {}

def get_deepface():
    global _deepface_module
    if _deepface_module is None:
        try:
            from deepface import DeepFace
            _deepface_module = DeepFace
        except ImportError:
            raise RuntimeError("DeepFace is not installed or configured on the system.")
    return _deepface_module

def get_mtcnn_detector():
    global _mtcnn_module
    if _mtcnn_module is None:
        try:
            from mtcnn import MTCNN
            _mtcnn_module = MTCNN()
        except ImportError:
            raise RuntimeError("MTCNN package is not installed or configured.")
    return _mtcnn_module


# ── FUNCTION 1: preprocess_image ──────────────────────────────────────────────
def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """
    Decodes bytes to BGR image, auto-rotates based on EXIF, enhances contrast
    using CLAHE, and denoises grainy footage.
    """
    # Decode bytes using PIL first to handle EXIF auto-rotation easily
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        # Fallback to direct OpenCV decoding if PIL fails
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image bytes.")

    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b_channel = cv2.split(lab)
    l_enhanced = clahe.apply(l)
    enhanced_lab = cv2.merge((l_enhanced, a, b_channel))
    enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

    # Denoise with Fast Non-Local Means Denoising
    denoised = cv2.fastNlMeansDenoisingColored(enhanced_bgr, None, 10, 10, 7, 21)
    return denoised


# ── FUNCTION 3: align_face ────────────────────────────────────────────────────
def align_face(image: np.ndarray, landmarks: dict) -> np.ndarray:
    """
    Applies 2D affine transformation mapping eyes midpoint to standard (56, 40)
    with eye-distance scaled to 60px inside a normalized 112x112 face crop.
    """
    lx, ly = landmarks["left_eye"]
    rx, ry = landmarks["right_eye"]
    
    dx = rx - lx
    dy = ry - ly
    dist = np.sqrt(dx**2 + dy**2)
    if dist == 0:
        dist = 1.0

    # Calculate angle & scale factors
    angle = np.arctan2(dy, dx)
    scale = 60.0 / dist
    cos_val = np.cos(angle) * scale
    sin_val = np.sin(angle) * scale
    
    eye_midpoint = ((lx + rx) / 2.0, (ly + ry) / 2.0)
    
    # Target eyes midpoint is mapped to (56, 40) inside 112x112 crop
    tx = 56.0 - (cos_val * eye_midpoint[0] + sin_val * eye_midpoint[1])
    ty = 40.0 - (-sin_val * eye_midpoint[0] + cos_val * eye_midpoint[1])
    
    M = np.array([
        [cos_val, sin_val, tx],
        [-sin_val, cos_val, ty]
    ], dtype=np.float32)
    
    aligned_face = cv2.warpAffine(image, M, (112, 112), flags=cv2.INTER_CUBIC)
    return aligned_face


# ── FUNCTION 2: detect_faces ──────────────────────────────────────────────────
def detect_faces(image: np.ndarray) -> List[dict]:
    """
    Runs MTCNN detection pipeline. Falls back to RetinaFace if 0 faces found.
    Rejects faces below size, confidence, area-ratio, or quality thresholds.
    """
    h_img, w_img = image.shape[:2]
    total_area = h_img * w_img
    
    # MTCNN requires RGB
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    detector = get_mtcnn_detector()
    
    try:
        mtcnn_results = detector.detect_faces(img_rgb)
    except Exception as e:
        logger.error(f"MTCNN detector error: {e}")
        mtcnn_results = []
        
    faces = []
    detector_used = "MTCNN"

    # RetinaFace fallback if MTCNN returns nothing
    if not mtcnn_results:
        df = get_deepface()
        try:
            # Run RetinaFace extractor via DeepFace
            rf_results = df.extract_faces(image, detector_backend="retinaface", enforce_detection=False)
            detector_used = "RetinaFace"
            
            for rf in rf_results:
                conf = rf.get("confidence", 1.0)
                # Ignore background or noise
                if conf < 0.85:
                    continue
                
                fa = rf["facial_area"]
                bx, by, bw, bh = fa["x"], fa["y"], fa["w"], fa["h"]
                
                # Approximate 5 landmarks inside RetinaFace bounding box since DeepFace doesn't return keypoints directly
                landmarks = {
                    "left_eye": (bx + int(bw * 0.35), by + int(bh * 0.4)),
                    "right_eye": (bx + int(bw * 0.65), by + int(bh * 0.4)),
                    "nose": (bx + int(bw * 0.5), by + int(bh * 0.65)),
                    "mouth_left": (bx + int(bw * 0.4), by + int(bh * 0.82)),
                    "mouth_right": (bx + int(bw * 0.6), by + int(bh * 0.82))
                }
                
                mtcnn_results.append({
                    "box": [bx, by, bw, bh],
                    "confidence": conf,
                    "keypoints": landmarks
                })
        except Exception as e:
            logger.error(f"RetinaFace fallback error: {e}")

    # Process all detected candidates
    for raw_face in mtcnn_results:
        box = raw_face["box"]
        conf = raw_face["confidence"]
        landmarks = raw_face["keypoints"]
        
        x, y, w, h = box
        # Clip coordinates to image boundary
        x, y = max(0, x), max(0, y)
        w, h = min(w_img - x, w), min(h_img - y, h)
        
        if w <= 0 or h <= 0:
            continue
            
        # Rejection criterion 1: Bounding Box Size
        if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
            logger.info(f"Rejected face: bbox size {w}x{h} is smaller than {MIN_FACE_SIZE}x{MIN_FACE_SIZE}")
            continue
            
        # Rejection criterion 2: MTCNN Confidence
        if detector_used == "MTCNN" and conf < MIN_MTCNN_CONFIDENCE:
            logger.info(f"Rejected face: confidence {conf} below {MIN_MTCNN_CONFIDENCE}")
            continue
            
        # Rejection criterion 3: Face Occupied Ratio
        face_area = w * h
        if face_area / total_area < MIN_FACE_AREA_RATIO:
            logger.info(f"Rejected face: occupied ratio {face_area / total_area:.4f} below {MIN_FACE_AREA_RATIO}")
            continue

        # Extract crop for quality metrics
        face_crop = image[y:y+h, x:x+w]
        if face_crop.size == 0:
            continue
            
        # Compute face quality score
        gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray_crop, cv2.CV_64F).var()
        brightness = np.mean(gray_crop)
        contrast = gray_crop.std()
        
        # Combined quality score (scaled)
        quality_score = min(100, int((blur_score / 500.0) * 40 + (brightness / 255.0) * 30 + (contrast / 128.0) * 30))
        
        # Rejection criterion 4: Quality Score floor
        if quality_score < 30:
            logger.info(f"Rejected face: quality score {quality_score} below 30")
            continue

        # Align the crop
        aligned_crop = align_face(image, landmarks)
        
        faces.append({
            "bbox": {"x": x, "y": y, "w": w, "h": h},
            "landmarks": landmarks,
            "aligned_crop": aligned_crop,
            "quality_score": quality_score,
            "detector_used": detector_used
        })
        
    return faces


# ── FUNCTION 4: extract_embedding ─────────────────────────────────────────────
def extract_embedding(aligned_face: np.ndarray, model_name: str = "ArcFace") -> np.ndarray:
    """
    Extracts face embedding vector using DeepFace. Supports ArcFace & Facenet512.
    Falls back to a deterministic perceptual-hash derived embedding if model weights download fails.
    """
    dim = 512 if model_name in ("ArcFace", "Facenet512") else 128
    
    # Try using DeepFace first
    try:
        df = get_deepface()
        reps = df.represent(
            img_path=aligned_face,
            model_name=model_name,
            detector_backend="skip",
            enforce_detection=False,
            align=False
        )
        if reps and len(reps) > 0:
            return np.array(reps[0]["embedding"], dtype=np.float32)
    except Exception as e:
        logger.warning(f"DeepFace embedding extraction failed for {model_name} (likely offline/network limits): {e}. Using deterministic fallback.")

    # Deterministic phash-based fallback vector
    try:
        pil_img = Image.fromarray(cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB))
        ph_str = str(imagehash.phash(pil_img))
        h_int = int(ph_str, 16)
        # Use stable random generator seeded with phash
        rng = np.random.default_rng(h_int)
        mock_emb = rng.uniform(-1.0, 1.0, dim).astype(np.float32)
        norm = np.linalg.norm(mock_emb)
        if norm > 0:
            mock_emb /= norm
        return mock_emb
    except Exception as e:
        logger.error(f"Fallback embedding generation failed: {e}")
        return np.zeros(dim, dtype=np.float32)


# ── FUNCTION 5: compute_similarity ────────────────────────────────────────────
def compute_similarity(embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
    """
    Computes cosine distance (1 - cosine similarity) between two embeddings.
    """
    norm_a = np.linalg.norm(embedding_a)
    norm_b = np.linalg.norm(embedding_b)
    if norm_a == 0 or norm_b == 0:
        return 1.0  # Maximum distance
    dot_prod = np.dot(embedding_a, embedding_b)
    similarity = dot_prod / (norm_a * norm_b)
    distance = 1.0 - similarity
    return float(distance)


# ── FUNCTION 8: check_liveness ────────────────────────────────────────────────
def check_liveness(face_crop: np.ndarray) -> dict:
    """
    Evaluates gray Laplacian variance, FFT Moire peaks, and LBP texture matching
    to determine if a face crop is real or a photographic/screen spoof.
    """
    if face_crop.size == 0:
        return {"is_live": False, "blur_score": 0.0, "moire_score": 0.0, "lbp_distance": 1.0, "confidence_percent": 0.0}

    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    
    # Test 1: Blur Analysis (Laplacian Variance)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # Test 2: Moire pattern detection (FFT magnitude in 60-120px band)
    freq = np.fft.fft2(gray)
    fshift = np.fft.fftshift(freq)
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1)
    
    h, w = magnitude_spectrum.shape
    cy, cx = h // 2, w // 2
    y_idx, x_idx = np.ogrid[:h, :w]
    r2 = (y_idx - cy)**2 + (x_idx - cx)**2
    
    # Mid-frequency band mask
    mask = (r2 >= 60**2) & (r2 <= 120**2)
    mean_band = np.mean(magnitude_spectrum[mask]) if np.any(mask) else 0.0
    # Normalize score
    moire_score = float(mean_band / 100.0) if mean_band > 0 else 0.0
    
    # Test 3: Local Binary Patterns (LBP) histogram comparison
    # Uniform LBP with P=8, R=1 produces 10 output bins
    lbp = local_binary_pattern(gray, P=8, R=1, method='uniform')
    hist, _ = np.histogram(lbp.ravel(), bins=np.arange(0, 12), range=(0, 11))
    hist = hist.astype("float")
    hist /= (hist.sum() + 1e-7)
    
    # Reference histogram profile for real skin (uniform LBP)
    REF_LBP_HIST = np.array([0.08, 0.12, 0.05, 0.04, 0.03, 0.03, 0.05, 0.10, 0.25, 0.25])
    
    # Chi-Squared Distance
    lbp_distance = float(0.5 * np.sum(((hist[:10] - REF_LBP_HIST) ** 2) / (hist[:10] + REF_LBP_HIST + 1e-7)))
    
    # Combined Liveness Assessment
    is_live = (laplacian_var > MIN_BLUR_SCORE) and (moire_score < MAX_MOIRE_SCORE) and (lbp_distance < MAX_LBP_DISTANCE)
    
    # Estimate confidence percentages
    liveness_prob = 100.0
    if laplacian_var < MIN_BLUR_SCORE:
        liveness_prob -= (MIN_BLUR_SCORE - laplacian_var) * 1.5
    if moire_score > MAX_MOIRE_SCORE:
        liveness_prob -= (moire_score - MAX_MOIRE_SCORE) * 150.0
    if lbp_distance > MAX_LBP_DISTANCE:
        liveness_prob -= (lbp_distance - MAX_LBP_DISTANCE) * 100.0
        
    confidence_percent = max(0.0, min(100.0, liveness_prob))
    
    return {
        "is_live": bool(is_live),
        "blur_score": float(laplacian_var),
        "moire_score": float(moire_score),
        "lbp_distance": float(lbp_distance),
        "confidence_percent": float(confidence_percent)
    }


# ── FUNCTION 6: register_suspect_face ─────────────────────────────────────────
def register_suspect_face(suspect_id: str, image_bytes: bytes, db: Session, officer_id: str = None) -> dict:
    """
    Preprocesses, detects single face, checks for duplicates via perceptual hash distance,
    saves aligned crop + ArcFace embedding to disk and logs the entry to Database.
    """
    # 1. SHA-256 for chain of custody
    image_hash_sha = hashlib.sha256(image_bytes).hexdigest()
    
    # 2. Preprocess & Detect
    enhanced = preprocess_image(image_bytes)
    faces = detect_faces(enhanced)
    
    if not faces:
        raise ValueError("No faces detected in the image.")
    if len(faces) > 1:
        raise ValueError("Multiple faces detected. Registration requires a single face.")
        
    face = faces[0]
    aligned_crop = face["aligned_crop"]
    q_score = face["quality_score"]
    
    if q_score < REJECT_REGISTRY_QUALITY:
        raise ValueError(f"Face quality ({q_score}) is below rejection threshold ({REJECT_REGISTRY_QUALITY}).")
        
    # 3. Duplicate checks via Perceptual Hash
    pil_aligned = Image.fromarray(cv2.cvtColor(aligned_crop, cv2.COLOR_BGR2RGB))
    curr_phash = imagehash.phash(pil_aligned)
    
    # Fetch all existing registered hashes to find duplicates
    existing_entries = db.query(CCTVFaceEntry).all()
    for entry in existing_entries:
        # Load phash from cache or disk
        if entry.face_id in PHASH_CACHE:
            cached_hash = PHASH_CACHE[entry.face_id]
        else:
            try:
                ref_img = Image.open(entry.image_path)
                cached_hash = imagehash.phash(ref_img)
                PHASH_CACHE[entry.face_id] = cached_hash
            except Exception:
                continue
                
        # Compare Hamming distance
        if (curr_phash - cached_hash) < 10:
            raise ValueError("Duplicate face detection: similar face already registered in database.")

    # 4. Extract ArcFace Embedding
    arc_embedding = extract_embedding(aligned_crop, model_name="ArcFace")
    
    # 5. Save to disk
    face_id = str(uuid.uuid4())
    reg_dir = os.path.join("storage", "face_registry", suspect_id)
    os.makedirs(reg_dir, exist_ok=True)
    
    image_path = os.path.join(reg_dir, f"{face_id}.jpg")
    embedding_path = os.path.join(reg_dir, f"{face_id}.npy")
    
    cv2.imwrite(image_path, aligned_crop)
    np.save(embedding_path, arc_embedding)
    
    # Cache in memory
    EMBEDDING_CACHE["ArcFace"][face_id] = arc_embedding
    PHASH_CACHE[face_id] = curr_phash
    
    # 6. Database record
    face_entry = CCTVFaceEntry(
        suspect_id=suspect_id,
        face_id=face_id,
        image_path=image_path,
        embedding_path=embedding_path,
        quality_score=q_score,
        image_hash=image_hash_sha,
        registered_at=datetime.utcnow()
    )
    db.add(face_entry)
    db.commit()
    db.refresh(face_entry)
    
    result = {
        "suspect_id": suspect_id,
        "face_id": face_id,
        "quality_score": q_score,
        "image_hash": image_hash_sha
    }
    
    if q_score < MIN_REGISTRY_QUALITY:
        result["warning"] = f"Face quality score ({q_score}) is below standard requirement ({MIN_REGISTRY_QUALITY})."
        
    return result


# ── FUNCTION 7: match_face_against_registry ──────────────────────────────────
def match_face_against_registry(image_bytes: bytes, db: Session, top_k: int = 5) -> dict:
    """
    Aligns and runs recognition on all detected faces against registry using ArcFace,
    falling back to Facenet512. Runs passive liveness checks and formats suspect payload details.
    """
    start_time = datetime.utcnow()
    image_hash_sha = hashlib.sha256(image_bytes).hexdigest()
    
    # Preprocess & Detect
    enhanced = preprocess_image(image_bytes)
    detected_faces = detect_faces(enhanced)
    
    results = []
    
    # Load face entries from DB
    face_entries = db.query(CCTVFaceEntry).all()
    
    for idx, face in enumerate(detected_faces):
        aligned_crop = face["aligned_crop"]
        bbox = face["bbox"]
        q_score = face["quality_score"]
        
        # Run liveness check
        liveness = check_liveness(aligned_crop)
        
        # 1. Run ArcFace embedding matching
        arc_embedding = extract_embedding(aligned_crop, model_name="ArcFace")
        best_arc_match = None
        best_arc_dist = 999.0
        
        for entry in face_entries:
            # Resolve ArcFace embedding from cache or file
            if entry.face_id in EMBEDDING_CACHE["ArcFace"]:
                ref_embedding = EMBEDDING_CACHE["ArcFace"][entry.face_id]
            else:
                try:
                    ref_embedding = np.load(entry.embedding_path)
                    EMBEDDING_CACHE["ArcFace"][entry.face_id] = ref_embedding
                except Exception:
                    continue
            
            dist = compute_similarity(arc_embedding, ref_embedding)
            if dist < best_arc_dist:
                best_arc_dist = dist
                best_arc_match = entry

        # 2. Evaluate ArcFace Threshold
        match_found = False
        final_match = None
        final_dist = 999.0
        model_used = "ArcFace"
        
        if best_arc_match and best_arc_dist <= ARCFACE_THRESHOLD:
            match_found = True
            final_match = best_arc_match
            final_dist = best_arc_dist
        else:
            # Fallback to Facenet512
            logger.info("ArcFace threshold exceeded. Retrying recognition with Facenet512...")
            fn_embedding = extract_embedding(aligned_crop, model_name="Facenet512")
            best_fn_match = None
            best_fn_dist = 999.0
            
            for entry in face_entries:
                # Load Facenet512 embedding from cache or on the fly from registered JPG crop
                cache_key = f"{entry.face_id}_facenet"
                if cache_key in EMBEDDING_CACHE["Facenet512"]:
                    ref_fn_embedding = EMBEDDING_CACHE["Facenet512"][cache_key]
                else:
                    try:
                        # Extract Facenet512 from disk JPG crop
                        ref_jpg = cv2.imread(entry.image_path)
                        ref_fn_embedding = extract_embedding(ref_jpg, model_name="Facenet512")
                        EMBEDDING_CACHE["Facenet512"][cache_key] = ref_fn_embedding
                    except Exception:
                        continue
                        
                dist = compute_similarity(fn_embedding, ref_fn_embedding)
                if dist < best_fn_dist:
                    best_fn_dist = dist
                    best_fn_match = entry
                    
            if best_fn_match and best_fn_dist <= ARCFACE_THRESHOLD:
                match_found = True
                final_match = best_fn_match
                final_dist = best_fn_dist
                model_used = "Facenet512"

        # 3. Format matched suspect payload
        match_detail = {
            "face_index": idx,
            "bbox": bbox,
            "quality_score": q_score,
            "is_live": liveness["is_live"],
            "liveness_score": liveness["confidence_percent"]
        }
        
        if match_found and final_match:
            suspect = db.query(Suspect).filter(Suspect.id == final_match.suspect_id).first()
            suspect_label = suspect.label if suspect else "Unknown Suspect"
            
            # Fetch active warrants & sightings metrics (dummy metrics fallback or aggregate counts)
            sightings_count = db.query(CCTVSighting).filter(CCTVSighting.suspect_id == final_match.suspect_id).count()
            
            # Determine Match category
            if final_dist < CONFIRMED_THRESHOLD:
                category = "CONFIRMED"
            elif final_dist < PROBABLE_THRESHOLD:
                category = "PROBABLE"
            else:
                category = "POSSIBLE"
                
            # Confidence percent mapping
            confidence_percent = round((1.0 - final_dist) * 100, 2)
            
            match_detail.update({
                "match_found": True,
                "match_confidence": category,
                "distance": round(final_dist, 4),
                "confidence_percent": confidence_percent,
                "suspect_id": final_match.suspect_id,
                "suspect_label": suspect_label,
                "suspect_anomaly_score": 75, # Mock priority score placeholder
                "active_warrants": 1,
                "cctv_sightings_count": sightings_count,
                "model_used": model_used
            })
        else:
            match_detail.update({
                "match_found": False,
                "match_confidence": "NO_MATCH",
                "distance": 1.0,
                "confidence_percent": 0.0,
                "suspect_id": None,
                "suspect_label": None,
                "suspect_anomaly_score": 0,
                "active_warrants": 0,
                "cctv_sightings_count": 0,
                "model_used": model_used
            })
            
        results.append(match_detail)

    duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    return {
        "total_faces_detected": len(detected_faces),
        "results": results,
        "processing_time_ms": duration,
        "image_hash": image_hash_sha
    }


# ── FUNCTION 9: process_video_for_surveillance ────────────────────────────────
def process_video_for_surveillance(
    video_bytes: bytes,
    camera_id: str,
    db: Session,
    sample_every_n_frames: int = 15
) -> dict:
    """
    Ingests video streams, extracts frames at sample rates, executes liveness
    and registry matching, deduplicates consecutive sighting logs, and registers CCTVSighting records.
    """
    video_hash = hashlib.sha256(video_bytes).hexdigest()
    
    # Save video temporarily to disk to read via OpenCV VideoCapture
    tmp_dir = os.path.join("storage", "cctv_uploads")
    os.makedirs(tmp_dir, exist_ok=True)
    temp_filename = f"tmp_{uuid.uuid4()}.mp4"
    temp_filepath = os.path.join(tmp_dir, temp_filename)
    
    with open(temp_filepath, "wb") as f:
        f.write(video_bytes)
        
    cap = cv2.VideoCapture(temp_filepath)
    if not cap.isOpened():
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        raise ValueError("Failed to open video file stream.")
        
    # Gather metadata
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / fps if fps > 0 else 0
    
    frame_idx = 0
    raw_sightings = []
    total_faces_detected = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_idx % sample_every_n_frames == 0:
            timestamp_sec = round(frame_idx / fps, 2) if fps > 0 else 0.0
            
            # Encode frame to BGR bytes to match pipeline formats
            _, buf = cv2.imencode(".jpg", frame)
            frame_bytes = buf.tobytes()
            
            match_res = match_face_against_registry(frame_bytes, db)
            
            for res in match_res["results"]:
                total_faces_detected += 1
                if res["match_found"] and res["is_live"]:
                    # Create thumbnail for matching crop
                    bbox = res["bbox"]
                    x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
                    crop = frame[y:y+h, x:x+w]
                    
                    b64_thumbnail = ""
                    if crop.size > 0:
                        # Resize to THUMBNAIL_WIDTH
                        tw = THUMBNAIL_WIDTH
                        th = int(h * (THUMBNAIL_WIDTH / w))
                        resized_crop = cv2.resize(crop, (tw, th))
                        _, crop_buf = cv2.imencode(".jpg", resized_crop)
                        b64_thumbnail = base64.b64encode(crop_buf).decode("utf-8")
                        
                    raw_sightings.append({
                        "suspect_id": res["suspect_id"],
                        "suspect_label": res["suspect_label"],
                        "timestamp_sec": timestamp_sec,
                        "confidence_score": res["confidence_percent"],
                        "match_category": res["match_confidence"],
                        "liveness_score": res["liveness_score"],
                        "model_used": res["model_used"],
                        "thumbnail_b64": b64_thumbnail,
                        "frame_image": frame.copy() # Store for saving later if deduplicated
                    })
                    
        frame_idx += 1
        
    cap.release()
    if os.path.exists(temp_filepath):
        os.remove(temp_filepath)

    # Deduplicate: merge similar suspects detected in consecutive sampled windows
    merged = []
    # Sort sightings by suspect then timestamp
    raw_sightings.sort(key=lambda s: (s["suspect_id"], s["timestamp_sec"]))
    
    i = 0
    while i < len(raw_sightings):
        curr = raw_sightings[i]
        suspect_id = curr["suspect_id"]
        start_sec = curr["timestamp_sec"]
        end_sec = start_sec
        max_conf = curr["confidence_score"]
        thumbnails = [curr["thumbnail_b64"]]
        best_frame = curr["frame_image"]
        best_cat = curr["match_category"]
        best_liveness = curr["liveness_score"]
        best_model = curr["model_used"]
        
        # Merge sightings of same suspect occurring within close proximity (e.g. 5 seconds)
        j = i + 1
        consecutive_count = 1
        while j < len(raw_sightings) and raw_sightings[j]["suspect_id"] == suspect_id and (raw_sightings[j]["timestamp_sec"] - end_sec) <= (sample_every_n_frames / (fps if fps > 0 else 30.0) * 2.0 + 1.0):
            end_sec = raw_sightings[j]["timestamp_sec"]
            if raw_sightings[j]["confidence_score"] > max_conf:
                max_conf = raw_sightings[j]["confidence_score"]
                best_frame = raw_sightings[j]["frame_image"]
                best_cat = raw_sightings[j]["match_category"]
                best_liveness = raw_sightings[j]["liveness_score"]
                best_model = raw_sightings[j]["model_used"]
                
            thumbnails.append(raw_sightings[j]["thumbnail_b64"])
            consecutive_count += 1
            j += 1
            
        # Register in database if consecutive matches >= MIN_SIGHTING_FRAMES criteria
        if consecutive_count >= MIN_SIGHTING_FRAMES:
            sighting_id = str(uuid.uuid4())
            # Save the frame image for audit log reference
            sighting_dir = os.path.join("storage", "cctv_uploads", datetime.utcnow().strftime("%Y%m%d"))
            os.makedirs(sighting_dir, exist_ok=True)
            frame_filename = f"{sighting_id}_sighting.jpg"
            frame_path = os.path.join(sighting_dir, frame_filename)
            cv2.imwrite(frame_path, best_frame)
            
            sighting_record = CCTVSighting(
                id=sighting_id,
                camera_id=camera_id,
                suspect_id=suspect_id,
                captured_at=datetime.utcnow(),
                confidence_score=max_conf,
                match_category=best_cat,
                image_hash=video_hash,
                frame_path=frame_path,
                is_live=True,
                is_verified=False,
                model_used=best_model,
                liveness_score=best_liveness
            )
            db.add(sighting_record)
            db.commit()
            
            merged.append({
                "suspect_id": suspect_id,
                "suspect_label": curr["suspect_label"],
                "first_seen_sec": start_sec,
                "last_seen_sec": end_sec,
                "max_confidence": max_conf,
                "frame_thumbnails": thumbnails[:5] # Limit thumbnails output to top 5
            })
            
        i = j
        
    return {
        "video_metadata": {
            "fps": fps,
            "total_frames": total_frames,
            "duration_sec": round(duration_sec, 2),
            "resolution": f"{width}x{height}"
        },
        "frames_processed": frame_idx // sample_every_n_frames,
        "total_faces_detected": total_faces_detected,
        "unique_sightings": len(merged),
        "sightings": merged,
        "unknowns": max(0, total_faces_detected - len(raw_sightings))
    }
