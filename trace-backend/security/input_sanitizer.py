import math
import re
import bleach

def sanitize_text(value: str) -> str:
    if not value:
        return ""
    
    # 1. Limit length to 10000 chars max
    if len(value) > 10000:
        value = value[:10000]
        
    # 2. Remove null bytes and control characters (except newline, tab)
    value = "".join(ch for ch in value if ch == "\n" or ch == "\r" or ch == "\t" or ord(ch) >= 32)
    value = value.replace("\x00", "")
    
    # 3. Reject strings containing SQL meta characters: --, ;--, /*, */, xp_
    forbidden_sql = ["--", ";--", "/*", "*/", "xp_"]
    val_lower = value.lower()
    for seq in forbidden_sql:
        if seq in val_lower:
            raise ValueError("Input contains forbidden SQL meta characters")
            
    # 4. Strip HTML tags
    value = bleach.clean(value, tags=[], attributes={}, strip=True)
    return value

def validate_file_upload(filename: str, content_type: str, file_bytes: bytes) -> bool:
    # 1. Reject files > 100MB (100 * 1024 * 1024 bytes)
    if len(file_bytes) > 100 * 1024 * 1024:
        return False
        
    # 2. Scan for null bytes in filename (path traversal prevention)
    if "\x00" in filename or "/" in filename or "\\" in filename:
        return False
        
    # 3. Whitelist allowed extensions
    allowed_extensions = {".csv", ".jpg", ".jpeg", ".png", ".mp4", ".avi"}
    fn_lower = filename.lower()
    matched_ext = None
    for ext in allowed_extensions:
        if fn_lower.endswith(ext):
            matched_ext = ext
            break
    if not matched_ext:
        return False
        
    # 4. Validate MIME/Magic Bytes matches extension
    # JPG: FF D8 FF
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    # MP4: ftyp (usually starts at offset 4)
    # AVI: RIFF at 0, AVI at 8
    # CSV: Plain text (should not contain non-printable control chars, except CR, LF, Tab)
    if matched_ext in {".jpg", ".jpeg"}:
        if len(file_bytes) < 3 or file_bytes[:3] != b"\xff\xd8\xff":
            return False
    elif matched_ext == ".png":
        if len(file_bytes) < 8 or file_bytes[:8] != b"\x89PNG\r\n\x1a\n":
            return False
    elif matched_ext == ".mp4":
        if len(file_bytes) < 12 or b"ftyp" not in file_bytes[4:12]:
            return False
    elif matched_ext == ".avi":
        if len(file_bytes) < 12 or file_bytes[:4] != b"RIFF" or file_bytes[8:12] != b"AVI ":
            return False
    elif matched_ext == ".csv":
        # Ensure it's mostly text, scan first 4096 bytes for binary zeros/executives
        sample = file_bytes[:4096]
        if b"\x00" in sample:
            return False
            
    return True

def validate_coordinates(lat: float, lon: float) -> bool:
    if lat is None or lon is None:
        return False
    
    # Reject NaN and Infinity values
    if not math.isfinite(lat) or not math.isfinite(lon):
        return False
        
    # lat must be between -90 and 90
    if not (-90.0 <= lat <= 90.0):
        return False
        
    # lon must be between -180 and 180
    if not (-180.0 <= lon <= 180.0):
        return False
        
    return True
