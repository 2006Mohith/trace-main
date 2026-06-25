# Legacy wrapper for backward compatibility. Re-exports upgraded cctv_engine.

import os
from engines.cctv_engine import (
    preprocess_image,
    detect_faces,
    align_face,
    extract_embedding,
    compute_similarity,
    check_liveness,
    register_suspect_face,
    match_face_against_registry,
    process_video_for_surveillance
)

def delete_suspect_face(suspect_id: str, face_id: str) -> bool:
    file_path = f"storage/face_registry/{suspect_id}/{face_id}"
    if os.path.exists(file_path):
        os.remove(file_path)
        # Clean up directory if empty
        registry_dir = f"storage/face_registry/{suspect_id}"
        if not os.listdir(registry_dir):
            os.rmdir(registry_dir)
        return True
    return False

# Backward compatible mappings
register_face = register_suspect_face
match_face = match_face_against_registry
process_video_frames = process_video_for_surveillance
