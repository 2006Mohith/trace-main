import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, Base, engine
from auth.models import Officer
from auth.routes import get_password_hash
from auth.mfa import generate_totp_secret, generate_backup_codes

def seed_officer():
    # Make sure all models are imported so metadata knows about them
    import models
    import auth.models
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if officer already exists
        existing = db.query(Officer).filter(Officer.badge_number == "ADMIN001").first()
        if existing:
            db.delete(existing)
            db.commit()
            print("Deleted existing ADMIN001 officer.")
            
        secret = generate_totp_secret()
        backup_codes = generate_backup_codes()
        
        # Default credentials
        password = "PrakasamPolice_2026!"
        hashed = get_password_hash(password)
        
        officer = Officer(
            badge_number="ADMIN001",
            hashed_password=hashed,
            role="SP",
            district="ongole",
            totp_secret=secret,
            backup_codes=",".join(backup_codes),
            is_active=True
        )
        db.add(officer)
        db.commit()
        db.refresh(officer)
        
        print("\n" + "="*50)
        print("SEEDING SUCCESSFUL - ADMINISTRATOR ACCOUNT CREATED")
        print("="*50)
        print(f"Badge Number: ADMIN001")
        print(f"Password:     {password}")
        print(f"Role:         SP (Superintendent of Police)")
        print(f"District:     ongole")
        print(f"TOTP Secret:  {secret}")
        print(f"Backup Codes: {', '.join(backup_codes)}")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"Seeding failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_officer()
