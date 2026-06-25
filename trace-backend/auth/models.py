import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, TypeDecorator, types
from database import Base
from security.encryption import encrypt_field, decrypt_field

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

def gen_uuid():
    return str(uuid.uuid4())

class Officer(Base):
    __tablename__ = "officers"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    badge_number = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # SP, INSPECTOR, CONSTABLE, ADMIN
    district = Column(Text, nullable=False)    # e.g., "ongole"
    
    # totp_secret is encrypted at rest using our custom TypeDecorator
    totp_secret = Column(EncryptedColumn, nullable=True)
    backup_codes = Column(EncryptedColumn, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
