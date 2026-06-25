import os
import sys
import shutil
import gzip
import logging
from datetime import datetime
from cryptography.fernet import Fernet

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from security.audit_logger import log_audit_enhanced

BACKUP_DIR = "storage/backups"
DB_FILE = "trace.db"

def run_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # 1. Verify source database exists
    if not os.path.exists(DB_FILE):
        print(f"Error: Database file '{DB_FILE}' not found.")
        return
        
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_gzip = os.path.join(BACKUP_DIR, f"trace_backup_{timestamp}.db.gz")
    backup_enc = os.path.join(BACKUP_DIR, f"trace_backup_{timestamp}.db.enc")
    
    db = SessionLocal()
    try:
        # 2. Compress database file with gzip
        with open(DB_FILE, 'rb') as f_in:
            with gzip.open(backup_gzip, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
                
        # 3. Read compressed data and encrypt it
        with open(backup_gzip, 'rb') as f:
            compressed_data = f.read()
            
        backup_key = os.getenv("BACKUP_ENCRYPTION_KEY")
        if not backup_key:
            # Fallback for dev: derive key or generate dummy key
            import base64
            backup_key = base64.urlsafe_b64encode(b"trace_backup_key_fallback_12345")
        else:
            # Ensure key is compatible with Fernet (must be 32 URL-safe base64 bytes)
            if len(backup_key) != 32:
                import base64
                backup_key = base64.urlsafe_b64encode(backup_key.ljust(32)[:32].encode())
                
        fernet = Fernet(backup_key)
        encrypted_data = fernet.encrypt(compressed_data)
        
        # 4. Write encrypted database backup file
        with open(backup_enc, 'wb') as f:
            f.write(encrypted_data)
            
        print(f"Backup created successfully: {backup_enc}")
        
        # 5. Log backup completion to database audit log
        log_audit_enhanced(
            db=db,
            action_type="DB_BACKUP_SUCCESS",
            entity_type="Database",
            entity_label="SQLite Database Backup",
            detail={"file": os.path.basename(backup_enc), "size_bytes": len(encrypted_data)}
        )
        
    except Exception as e:
        print(f"Backup failed: {e}")
        try:
            log_audit_enhanced(
                db=db,
                action_type="DB_BACKUP_FAILURE",
                entity_type="Database",
                detail={"error": str(e)},
                status="FAILURE"
            )
        except Exception:
            pass
    finally:
        db.close()
        # Clean up temporary gzip file
        if os.path.exists(backup_gzip):
            os.remove(backup_gzip)
            
    # 6. Retention Policy: Keep last 14 backups, delete older ones
    try:
        all_backups = []
        for f in os.listdir(BACKUP_DIR):
            if f.startswith("trace_backup_") and f.endswith(".db.enc"):
                path = os.path.join(BACKUP_DIR, f)
                all_backups.append((path, os.path.getmtime(path)))
                
        # Sort by modification time ascending (oldest first)
        all_backups.sort(key=lambda x: x[1])
        
        if len(all_backups) > 14:
            to_delete = all_backups[:-14]
            for path, _ in to_delete:
                os.remove(path)
                print(f"Deleted old backup: {path}")
    except Exception as e:
        print(f"Failed to clean up old backups: {e}")

if __name__ == "__main__":
    run_backup()
