import uuid
import json
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float,
    DateTime, ForeignKey, TypeDecorator, types, Boolean
)
from sqlalchemy.orm import relationship
from database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ── Cross-DB JSON column (works on both SQLite and PostgreSQL) ─────────────────
class JSONColumn(TypeDecorator):
    """Stores JSON as text on SQLite; uses native JSONB on Postgres."""
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value   # PostgreSQL JSONB already deserialized
        return json.loads(value)


# ── Models ─────────────────────────────────────────────────────────────────────

class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    suspects = relationship("Suspect", back_populates="case", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="case", cascade="all, delete-orphan")


class Suspect(Base):
    __tablename__ = "suspects"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    label = Column(Text, nullable=False)
    primary_msisdn = Column(Text, nullable=False)

    case = relationship("Case", back_populates="suspects")
    cdr_records = relationship("CDRRecord", back_populates="suspect", cascade="all, delete-orphan")
    ipdr_records = relationship("IPDRRecord", back_populates="suspect", cascade="all, delete-orphan")


class CDRRecord(Base):
    __tablename__ = "cdr_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    suspect_id = Column(String(36), ForeignKey("suspects.id"), nullable=False)
    msisdn_a = Column(Text, nullable=False)
    msisdn_b = Column(Text, nullable=False)
    imei = Column(Text)
    tower_id = Column(Text)
    tower_lat = Column(Float)
    tower_lon = Column(Float)
    call_type = Column(Text)
    duration_sec = Column(Integer)
    timestamp = Column(DateTime, nullable=False)

    suspect = relationship("Suspect", back_populates="cdr_records")


class IPDRRecord(Base):
    __tablename__ = "ipdr_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    suspect_id = Column(String(36), ForeignKey("suspects.id"), nullable=False)
    msisdn = Column(Text, nullable=False)
    dest_ip = Column(Text, nullable=False)
    dest_port = Column(Integer)
    data_volume_kb = Column(Float)
    app_label = Column(Text)
    timestamp = Column(DateTime, nullable=False)

    suspect = relationship("Suspect", back_populates="ipdr_records")


class Event(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    event_type = Column(Text, nullable=False)
    severity = Column(Text, nullable=False)
    # Stored as JSON list ["Suspect A", "Suspect B"]
    involved_suspects = Column(JSONColumn, nullable=False, default=list)
    # Stored as JSON dict
    detail = Column(JSONColumn, nullable=False, default=dict)
    occurred_at = Column(DateTime)

    case = relationship("Case", back_populates="events")


# ── Encrypted Columns ──────────────────────────────────────────────────────────
from security.encryption import encrypt_field, encrypt_searchable_field, decrypt_field

class EncryptedColumn(TypeDecorator):
    """Automatically encrypts values on write and decrypts on read."""
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_field(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_field(value)

class SearchableEncryptedColumn(TypeDecorator):
    """Encrypts value with searchable prefix on write and decrypts on read."""
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_searchable_field(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_field(value)


# ── Audit Log ──────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    # Action type: ANALYSIS_RUN, REPORT_GENERATED, SUSPECT_ADDED,
    #              SUSPECT_DELETED, CASE_CREATED, CDR_UPLOADED, IPDR_UPLOADED
    action_type = Column(Text, nullable=False)
    # Entity: Case, Suspect, Report
    entity_type = Column(Text, nullable=False)
    entity_id = Column(Text, nullable=True)
    entity_label = Column(Text, nullable=True)   # human-readable name
    # Officer / Session info - Encrypted but searchable via hash index
    officer_ip = Column(SearchableEncryptedColumn, nullable=True)
    officer_host = Column(Text, nullable=True)
    # Structured extra detail
    detail = Column(JSONColumn, nullable=True, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


# ── CCTV & DeepFace Cameras ────────────────────────────────────────────────────

class CCTVCamera(Base):
    __tablename__ = "cctv_cameras"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    camera_id = Column(String(50), unique=True, index=True, nullable=False)  # e.g., ONG-CAM-01
    location_name = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String(20), default="ONLINE", nullable=False)  # ONLINE, OFFLINE, MAINTENANCE
    last_ping = Column(DateTime, default=datetime.utcnow)
    
    # Encrypted RTSP URL
    rtsp_url = Column(EncryptedColumn, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CCTVFaceEntry(Base):
    __tablename__ = "cctv_face_entries"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    suspect_id = Column(String(36), ForeignKey("suspects.id"), nullable=False)
    face_id = Column(Text, nullable=False)
    image_path = Column(Text, nullable=False)
    embedding_path = Column(Text, nullable=False)
    quality_score = Column(Integer)
    image_hash = Column(Text)                                # SHA-256
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CCTVSighting(Base):
    __tablename__ = "cctv_sightings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    camera_id = Column(String(50), ForeignKey("cctv_cameras.camera_id"), nullable=False)
    suspect_id = Column(String(36), ForeignKey("suspects.id"), nullable=True)  # Nullable if unknown suspect
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confidence_score = Column(Float, nullable=False)
    match_category = Column(Text)                            # CONFIRMED|PROBABLE|POSSIBLE
    image_hash = Column(Text, nullable=False)                # SHA-256 of original frame
    frame_path = Column(Text, nullable=False)                # Local file path to stored frame
    is_live = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by = Column(Text, nullable=True)
    model_used = Column(Text)                                # ArcFace|Facenet512
    liveness_score = Column(Float)


# ── AI Case Investigator ──────────────────────────────────────────────────────

class AIInvestigationReport(Base):
    __tablename__ = "ai_investigation_reports"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    generated_by_officer_id = Column(String(36), nullable=False)
    model_used = Column(Text, nullable=False)
    report_json = Column(JSONColumn, nullable=False)
    input_token_count = Column(Integer, default=0)
    output_token_count = Column(Integer, default=0)


class AIChatSession(Base):
    __tablename__ = "ai_chat_sessions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    officer_id = Column(String(36), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    messages = Column(JSONColumn, nullable=False, default=list)


