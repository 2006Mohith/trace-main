import os
import sys

# Setup python path to import local modules correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Suspect
from routers.report import _build_pdf

def main():
    db = SessionLocal()
    suspect = db.query(Suspect).filter(Suspect.label == "Kalyan Chakravarthy").first()
    if not suspect:
        print("Kalyan Chakravarthy not found, fetching any suspect")
        suspect = db.query(Suspect).first()
    if not suspect:
        print("No suspect found in DB!")
        return

    print(f"Generating PDF report for suspect: {suspect.label}...")
    pdf_bytes = _build_pdf(suspect, db)
    
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "sample_court_report.pdf")
    
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)
        
    print(f"Sample PDF report saved successfully to {out_path}!")
    db.close()

if __name__ == "__main__":
    main()
