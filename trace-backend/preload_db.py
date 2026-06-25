"""
preload_db.py
Preloads Case 1, Case 2, and Case 3 from demo-data/ CSV files directly into the SQLite database.
Runs the analytical engines for each case to pre-populate all intelligence events.

Usage:
    python preload_db.py
"""

import os
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session

# Setup python path to import local modules correctly
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Base
from models import Case, Suspect, CDRRecord, IPDRRecord, Event
from engines.imei_swap import detect_imei_swaps
from engines.co_location import detect_co_location
from engines.common_contact import detect_common_contacts
from engines.anomaly import detect_anomalies
from engines.ott_fingerprint import fingerprint_ott

DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo-data")

def parse_datetime(val):
    val_str = str(val).strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S"):
        try:
            return pd.to_datetime(val_str, format=fmt)
        except:
            continue
    return pd.to_datetime(val_str, errors="coerce")

def preload_suspect(db: Session, case_id: str, label: str, cdr_filename: str, ipdr_filename: str = None):
    cdr_path = os.path.join(DEMO_DIR, cdr_filename)
    if not os.path.exists(cdr_path):
        print(f"  Warning: CDR file {cdr_filename} not found, skipping suspect {label}")
        return None

    cdr_df = pd.read_csv(cdr_path)
    cdr_df["timestamp"] = cdr_df["timestamp"].apply(parse_datetime)
    cdr_df["timestamp"] = cdr_df["timestamp"].fillna(datetime.utcnow())
    cdr_df["duration_sec"] = pd.to_numeric(cdr_df["duration_sec"], errors="coerce").fillna(0).astype(int)
    cdr_df["tower_lat"] = pd.to_numeric(cdr_df["tower_lat"], errors="coerce")
    cdr_df["tower_lon"] = pd.to_numeric(cdr_df["tower_lon"], errors="coerce")

    # Primary MSISDN
    primary_msisdn = str(cdr_df["msisdn_a"].mode().iloc[0]) if not cdr_df.empty else "UNKNOWN"

    suspect = Suspect(case_id=case_id, label=label, primary_msisdn=primary_msisdn)
    db.add(suspect)
    db.flush()

    # CDR
    cdr_rows = []
    for _, row in cdr_df.iterrows():
        cdr_rows.append(CDRRecord(
            suspect_id=suspect.id,
            msisdn_a=str(row["msisdn_a"]),
            msisdn_b=str(row["msisdn_b"]),
            imei=str(row["imei"]) if pd.notna(row["imei"]) else None,
            tower_id=str(row["tower_id"]) if pd.notna(row["tower_id"]) else None,
            tower_lat=float(row["tower_lat"]) if pd.notna(row["tower_lat"]) else None,
            tower_lon=float(row["tower_lon"]) if pd.notna(row["tower_lon"]) else None,
            call_type=str(row["call_type"]) if pd.notna(row["call_type"]) else None,
            duration_sec=int(row["duration_sec"]),
            timestamp=row["timestamp"].to_pydatetime(),
        ))
    db.add_all(cdr_rows)

    # IPDR
    if ipdr_filename:
        ipdr_path = os.path.join(DEMO_DIR, ipdr_filename)
        if os.path.exists(ipdr_path):
            ipdr_df = pd.read_csv(ipdr_path)
            ipdr_df["timestamp"] = ipdr_df["timestamp"].apply(parse_datetime)
            ipdr_df["timestamp"] = ipdr_df["timestamp"].fillna(datetime.utcnow())
            ipdr_df["data_volume_kb"] = pd.to_numeric(ipdr_df["data_volume_kb"], errors="coerce").fillna(0)
            ipdr_df["dest_port"] = pd.to_numeric(ipdr_df["dest_port"], errors="coerce").fillna(0).astype(int)

            ipdr_rows = []
            for _, row in ipdr_df.iterrows():
                ipdr_rows.append(IPDRRecord(
                    suspect_id=suspect.id,
                    msisdn=str(row["msisdn"]),
                    dest_ip=str(row["dest_ip"]),
                    dest_port=int(row["dest_port"]),
                    data_volume_kb=float(row["data_volume_kb"]),
                    app_label="Unknown",
                    timestamp=row["timestamp"].to_pydatetime(),
                ))
            db.add_all(ipdr_rows)

    db.commit()
    db.refresh(suspect)
    print(f"  Ingested suspect: {label} ({len(cdr_rows)} CDR records, {ipdr_filename and 'with IPDR' or 'no IPDR'})")
    return suspect

def run_analysis_for_case(db: Session, case_id: str):
    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()
    if not suspects:
        return

    # Clear old events
    db.query(Event).filter(Event.case_id == case_id).delete()

    event_counts = {
        "imei_swaps": 0,
        "co_locations": 0,
        "common_contacts": 0,
        "anomalies": 0,
        "ott_flags": 0,
    }

    # IMEI swaps
    for suspect in suspects:
        events = detect_imei_swaps(suspect.id, db)
        for ev in events:
            db.add(ev)
        event_counts["imei_swaps"] += len(events)

    # Co-location
    co_events = detect_co_location(case_id, db)
    for ev in co_events:
        db.add(ev)
    event_counts["co_locations"] = len(co_events)

    # Common contacts
    cc_events = detect_common_contacts(case_id, db)
    for ev in cc_events:
        db.add(ev)
    event_counts["common_contacts"] = len(cc_events)

    # Anomaly detection
    anomaly_events = detect_anomalies(case_id, db)
    for ev in anomaly_events:
        db.add(ev)
    event_counts["anomalies"] = len(anomaly_events)

    # OTT usage
    for suspect in suspects:
        ott_events = fingerprint_ott(suspect.id, db)
        for ev in ott_events:
            db.add(ev)
        event_counts["ott_flags"] += len(ott_events)

    db.commit()
    total = sum(event_counts.values())
    print(f"  Analysis ran: {total} events generated ({event_counts})")

def main():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    print("Clearing existing cases...")
    db.query(Event).delete()
    db.query(CDRRecord).delete()
    db.query(IPDRRecord).delete()
    db.query(Suspect).delete()
    db.query(Case).delete()
    db.commit()

    # ══════════════════════════════════════════════════════════════════════════
    # CASE 1: Ongole Tobacco Smuggling Syndicate (FIR 124/2026)
    # ══════════════════════════════════════════════════════════════════════════
    print("\nPreloading Case 1: Ongole Tobacco Smuggling Syndicate (FIR 124/2026)")
    case1 = Case(name="Ongole Tobacco Smuggling Syndicate (FIR 124/2026)")
    db.add(case1)
    db.commit()
    db.refresh(case1)

    preload_suspect(db, case1.id, "Kalyan Chakravarthy", 
                    "Case1_Ongole_Tobacco_Smuggling_CDR_Kalyan_Chakravarthy.csv", 
                    "Case1_Ongole_Tobacco_Smuggling_IPDR_Kalyan_Chakravarthy.csv")
    preload_suspect(db, case1.id, "Venkatesh Prasad", 
                    "Case1_Ongole_Tobacco_Smuggling_CDR_Venkatesh_Prasad.csv", 
                    "Case1_Ongole_Tobacco_Smuggling_IPDR_Venkatesh_Prasad.csv")
    preload_suspect(db, case1.id, "Subba Rao", 
                    "Case1_Ongole_Tobacco_Smuggling_CDR_Subba_Rao.csv")
    preload_suspect(db, case1.id, "Ananthakrishna", 
                    "Case1_Ongole_Tobacco_Smuggling_CDR_Ananthakrishna.csv")
    preload_suspect(db, case1.id, "Anjali Devi", 
                    "Case1_Ongole_Tobacco_Smuggling_CDR_Anjali_Devi.csv")

    run_analysis_for_case(db, case1.id)

    # ══════════════════════════════════════════════════════════════════════════
    # CASE 2: Hyderabad–Guntur Cyber Fraud Network (FIR 135/2026)
    # ══════════════════════════════════════════════════════════════════════════
    print("\nPreloading Case 2: Hyderabad–Guntur Cyber Fraud Network (FIR 135/2026)")
    case2 = Case(name="Hyderabad–Guntur Cyber Fraud Network (FIR 135/2026)")
    db.add(case2)
    db.commit()
    db.refresh(case2)

    preload_suspect(db, case2.id, "Ranga Reddy", 
                    "Case2_Hyd_Gnt_Cyber_Fraud_CDR_Ranga_Reddy.csv", 
                    "Case2_Hyd_Gnt_Cyber_Fraud_IPDR_Ranga_Reddy.csv")
    preload_suspect(db, case2.id, "Srinivas Rao", 
                    "Case2_Hyd_Gnt_Cyber_Fraud_CDR_Srinivas_Rao.csv", 
                    "Case2_Hyd_Gnt_Cyber_Fraud_IPDR_Srinivas_Rao.csv")
    preload_suspect(db, case2.id, "Venkateswara Rao", 
                    "Case2_Hyd_Gnt_Cyber_Fraud_CDR_Venkateswara_Rao.csv")
    preload_suspect(db, case2.id, "Lalitha Prasad", 
                    "Case2_Hyd_Gnt_Cyber_Fraud_CDR_Lalitha_Prasad.csv")

    run_analysis_for_case(db, case2.id)

    # ══════════════════════════════════════════════════════════════════════════
    # CASE 3: Visakhapatnam Port Contraband Ring (FIR 201/2026)
    # ══════════════════════════════════════════════════════════════════════════
    print("\nPreloading Case 3: Visakhapatnam Port Contraband Ring (FIR 201/2026)")
    case3 = Case(name="Visakhapatnam Port Contraband Ring (FIR 201/2026)")
    db.add(case3)
    db.commit()
    db.refresh(case3)

    preload_suspect(db, case3.id, "Tirupati Naidu", 
                    "Case3_Vizag_Contraband_Cartel_CDR_Tirupati_Naidu.csv", 
                    "Case3_Vizag_Contraband_Cartel_IPDR_Tirupati_Naidu.csv")
    preload_suspect(db, case3.id, "Madhav Prasad", 
                    "Case3_Vizag_Contraband_Cartel_CDR_Madhav_Prasad.csv", 
                    "Case3_Vizag_Contraband_Cartel_IPDR_Madhav_Prasad.csv")
    preload_suspect(db, case3.id, "Satyanarayana", 
                    "Case3_Vizag_Contraband_Cartel_CDR_Satyanarayana.csv")

    run_analysis_for_case(db, case3.id)

    db.close()
    print("\nDatabase fully preloaded with three legit cases and analysis!")

if __name__ == "__main__":
    main()
