# CCTV Precision Tuning Constants

# DETECTION
MIN_FACE_SIZE = 40              # pixels (width and height)
MIN_MTCNN_CONFIDENCE = 0.95    # reject uncertain detections
MIN_FACE_AREA_RATIO = 0.005    # face must be 0.5% of image

# RECOGNITION
ARCFACE_THRESHOLD = 0.40       # cosine distance cutoff
CONFIRMED_THRESHOLD = 0.25     # distance below = confirmed match
PROBABLE_THRESHOLD = 0.35      # distance below = probable match
FALLBACK_MODEL = "Facenet512"  # used when ArcFace finds no match
EMBEDDING_CACHE_SIZE = 1000    # max cached embeddings in memory

# LIVENESS
MIN_BLUR_SCORE = 60            # laplacian variance floor
MAX_MOIRE_SCORE = 0.15         # FFT moire detection ceiling
MAX_LBP_DISTANCE = 0.50        # LBP texture ceiling

# VIDEO
DEFAULT_SAMPLE_RATE = 15       # process every Nth frame
MIN_SIGHTING_FRAMES = 3        # min consecutive matches to create sighting
MAX_VIDEO_SIZE_MB = 500        # reject videos larger than this
THUMBNAIL_WIDTH = 128          # face thumbnail width for API response

# QUALITY
MIN_REGISTRY_QUALITY = 50      # warn if registered face below this
REJECT_REGISTRY_QUALITY = 25   # hard reject if below this
