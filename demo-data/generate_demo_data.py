import os
import csv
import random
from datetime import datetime, timedelta

random.seed(42)
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Strict AP/Telangana Coordinate boundaries (12.6 to 19.9 Lat, 76.7 to 84.8 Lon)
TOWERS = {
    # Prakasham District Towers
    "TWR-ONG-001": {"name": "Ongole Central",       "lat": 15.5057, "lon": 80.0499, "district": "Prakasham"},
    "TWR-ONG-002": {"name": "Ongole Bus Stand",     "lat": 15.5100, "lon": 80.0450, "district": "Prakasham"},
    "TWR-CDD-001": {"name": "Chirala Prakasham",    "lat": 15.8167, "lon": 80.3500, "district": "Prakasham"},
    "TWR-MRT-001": {"name": "Markapur Prakasham",   "lat": 15.7333, "lon": 79.2667, "district": "Prakasham"},
    "TWR-KAN-001": {"name": "Kandukur Prakasham",   "lat": 15.2167, "lon": 79.9000, "district": "Prakasham"},
    "TWR-ADK-001": {"name": "Addanki Prakasham",    "lat": 15.7500, "lon": 79.9750, "district": "Prakasham"},
    "TWR-PDL-001": {"name": "Podili Prakasham",     "lat": 15.4667, "lon": 79.5833, "district": "Prakasham"},
    "TWR-DRS-001": {"name": "Darsi Prakasham",      "lat": 15.7667, "lon": 79.6833, "district": "Prakasham"},
    
    # Regional Towers (AP/Telangana)
    "TWR-HYD-001": {"name": "Hyderabad Secunderabad","lat": 17.4399, "lon": 78.4983, "district": "Hyderabad"},
    "TWR-HYD-002": {"name": "LB Nagar Hyderabad",   "lat": 17.3453, "lon": 78.5479, "district": "Hyderabad"},
    "TWR-GNT-001": {"name": "Guntur Junction",      "lat": 16.3067, "lon": 80.4365, "district": "Guntur"},
    "TWR-VJA-001": {"name": "Vijayawada Central",   "lat": 16.5062, "lon": 80.6480, "district": "Krishna"},
    "TWR-NLR-001": {"name": "Nellore Town",         "lat": 14.4426, "lon": 79.9865, "district": "Nellore"},
    "TWR-KNL-001": {"name": "Kurnool City",         "lat": 15.8281, "lon": 78.0373, "district": "Kurnool"},
    "TWR-VZG-001": {"name": "Visakhapatnam Harbor",  "lat": 17.6800, "lon": 83.2100, "district": "Visakhapatnam"},
    "TWR-KKD-001": {"name": "Kakinada Port",        "lat": 16.9800, "lon": 82.2600, "district": "East Godavari"},
    "TWR-RJY-001": {"name": "Rajahmundry Bypass",   "lat": 17.0000, "lon": 81.8000, "district": "East Godavari"},
}

START_DATE = datetime(2026, 6, 1, 0, 0, 0)

# Helper function to generate timestamps
def rand_ts(day: int, hour_min: int = 0, hour_max: int = 23) -> datetime:
    base = START_DATE + timedelta(days=day - 1)
    h = random.randint(hour_min, hour_max)
    m = random.randint(0, 59)
    s = random.randint(0, 59)
    return base.replace(hour=h, minute=m, second=s)

def fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def write_csv(path: str, header: list, rows: list):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  Generated {len(rows):>4} rows -> {os.path.basename(path)}")

# ══════════════════════════════════════════════════════════════════════════════
# CASE 1: Ongole Tobacco Smuggling Syndicate (Prakasham District)
# ══════════════════════════════════════════════════════════════════════════════
def gen_case_1():
    print("Generating Case 1...")
    case_prefix = "Case1_Ongole_Tobacco_Smuggling"
    
    # Suspects & contacts
    msisdn_a = "919440123456"  # Kalyan Chakravarthy
    msisdn_b = "919963987654"  # Venkatesh Prasad
    msisdn_c = "919849000312"  # Subba Rao
    msisdn_d = "919000100004"  # Ananthakrishna
    msisdn_e = "919848011223"  # Anjali Devi (Clean Control)
    handler = "919888000111"   # Venkata Ramana
    
    contacts_pool = ["919177234560", "919032456789", "919849234567", "918074561234",
                     "918341567890", "919000112233", "917330198765", "919848111222"]
    
    # ── Suspect A: Kalyan Chakravarthy (Anomalous Kingpin) ──
    # Bursts on Day 1-2, IMEI swap on Day 3, goes silent on Day 4. Night ratio > 70%
    cdr_a = []
    # Day 1: Burst calls (Ongole Central)
    twr_a = TOWERS["TWR-ONG-001"]
    imei_old = "359876123400001"
    imei_new = "490876123499999"
    
    # Day 1: 22 calls
    for _ in range(22):
        ts = rand_ts(1, 21, 23) if random.random() < 0.75 else rand_ts(1, 6, 20)
        dest = random.choice([msisdn_b, msisdn_c, msisdn_d, handler] + contacts_pool)
        cdr_a.append([msisdn_a, dest, imei_old, "TWR-ONG-001", twr_a["lat"], twr_a["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])
    
    # Day 2: 24 calls, and co-location event at Chirala
    twr_cdd = TOWERS["TWR-CDD-001"]
    # Co-location call at 15:05
    coloc_ts = START_DATE + timedelta(days=1, hours=15, minutes=5)
    cdr_a.append([msisdn_a, msisdn_b, imei_old, "TWR-CDD-001", twr_cdd["lat"], twr_cdd["lon"], "CALL", 180, fmt_ts(coloc_ts)])
    for _ in range(23):
        ts = rand_ts(2, 23, 23) if random.random() < 0.75 else rand_ts(2, 6, 20)
        dest = random.choice([msisdn_b, msisdn_c, handler] + contacts_pool)
        # Randomly choose Ongole or Chirala tower
        twr = random.choice([TOWERS["TWR-ONG-001"], TOWERS["TWR-ONG-002"]])
        cdr_a.append([msisdn_a, dest, imei_old, "TWR-ONG-001", twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])
        
    # Day 3: IMEI Swap at 02:30. 10 calls.
    swap_ts = START_DATE + timedelta(days=2, hours=2, minutes=30)
    cdr_a.append([msisdn_a, handler, imei_new, "TWR-ONG-001", twr_a["lat"], twr_a["lon"], "CALL", 60, fmt_ts(swap_ts)]) # new IMEI call
    for i in range(9):
        ts = rand_ts(3, 3, 23)
        imei = imei_old if ts < swap_ts else imei_new
        dest = random.choice([msisdn_b, handler] + contacts_pool)
        cdr_a.append([msisdn_a, dest, imei, "TWR-ONG-001", twr_a["lat"], twr_a["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])
        
    # Day 4: Go silent (0 calls, which satisfies silence_after_burst < peak_count * 0.5)
    
    # Days 5-30: sparse calling, night-focused
    for day in range(5, 31):
        if random.random() < 0.3:  # call on some days
            for _ in range(random.randint(1, 3)):
                ts = rand_ts(day, 23, 23) if random.random() < 0.8 else rand_ts(day, 8, 17)
                dest = random.choice([msisdn_b, handler] + contacts_pool)
                twr = random.choice([TOWERS["TWR-ONG-001"], TOWERS["TWR-ONG-002"], TOWERS["TWR-MRT-001"]])
                cdr_a.append([msisdn_a, dest, imei_new, twr["name"], twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])

    cdr_a.sort(key=lambda x: x[8])
    
    # ── Suspect B: Venkatesh Prasad (Co-conspirator) ──
    cdr_b = []
    imei_b = "352098765432100"
    # Calls handler, Kalyan, Subba Rao
    for day in range(1, 31):
        # Day 2: Co-location call at Chirala at 15:00
        if day == 2:
            coloc_ts_b = START_DATE + timedelta(days=1, hours=15, minutes=0)
            cdr_b.append([msisdn_b, msisdn_a, imei_b, "TWR-CDD-001", twr_cdd["lat"], twr_cdd["lon"], "CALL", 120, fmt_ts(coloc_ts_b)])
        
        n_calls = random.randint(2, 6)
        for _ in range(n_calls):
            ts = rand_ts(day, 8, 22)
            dest = random.choice([msisdn_a, msisdn_c, handler] + contacts_pool)
            twr = TOWERS["TWR-CDD-001"] if day < 10 else TOWERS["TWR-ONG-002"]
            cdr_b.append([msisdn_b, dest, imei_b, "TWR-CDD-001", twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])
            
    cdr_b.sort(key=lambda x: x[8])
    
    # ── Suspect C: Subba Rao (Co-conspirator) ──
    cdr_c = []
    imei_c = "356001122334455"
    for day in range(1, 31):
        if day == 2:
            coloc_ts_c = START_DATE + timedelta(days=1, hours=15, minutes=15)
            cdr_c.append([msisdn_c, msisdn_a, imei_c, "TWR-CDD-001", twr_cdd["lat"], twr_cdd["lon"], "CALL", 150, fmt_ts(coloc_ts_c)])
            
        n_calls = random.randint(1, 4)
        for _ in range(n_calls):
            ts = rand_ts(day, 9, 20)
            dest = random.choice([msisdn_a, msisdn_b, handler] + contacts_pool)
            twr = TOWERS["TWR-KAN-001"]
            cdr_c.append([msisdn_c, dest, imei_c, "TWR-KAN-001", twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])
            
    cdr_c.sort(key=lambda x: x[8])

    # ── Suspect D: Ananthakrishna (Buyer/Associate) ──
    cdr_d = []
    imei_d = "351234567890004"
    for day in range(1, 31):
        n_calls = random.randint(1, 3)
        for _ in range(n_calls):
            ts = rand_ts(day, 10, 18)
            dest = random.choice([msisdn_b, msisdn_c])
            twr = TOWERS["TWR-NLR-001"]
            cdr_d.append([msisdn_d, dest, imei_d, "TWR-NLR-001", twr["lat"], twr["lon"], "CALL", random.randint(30, 200), fmt_ts(ts)])
            
    cdr_d.sort(key=lambda x: x[8])

    # ── Suspect E: Anjali Devi (Clean Control) ──
    cdr_e = []
    imei_e = "351234567890005"
    family_contacts = ["919177001001", "919177001002", "919177001003"]
    for day in range(1, 31):
        n_calls = random.randint(2, 4)
        for _ in range(n_calls):
            ts = rand_ts(day, 8, 20)
            dest = random.choice(family_contacts)
            twr = TOWERS["TWR-ONG-001"]
            cdr_e.append([msisdn_e, dest, imei_e, "TWR-ONG-001", twr["lat"], twr["lon"], "CALL", random.randint(60, 400), fmt_ts(ts)])
            
    cdr_e.sort(key=lambda x: x[8])

    # ── IPDR Suspect A (WhatsApp & Telegram OTT) ──
    # Columns: msisdn, dest_ip, dest_port, data_volume_kb, timestamp
    ipdr_a = []
    for day in range(1, 31):
        for _ in range(random.randint(4, 10)):
            ts = rand_ts(day, 0, 23)
            # WhatsApp
            ipdr_a.append([msisdn_a, "157.240.198.35", 443, round(random.uniform(50.0, 5000.0), 2), fmt_ts(ts)])
        for _ in range(random.randint(2, 6)):
            ts = rand_ts(day, 0, 23)
            # Telegram
            ipdr_a.append([msisdn_a, "149.154.167.91", 443, round(random.uniform(30.0, 2000.0), 2), fmt_ts(ts)])
    ipdr_a.sort(key=lambda x: x[4])

    # ── IPDR Suspect B (Standard traffic) ──
    ipdr_b = []
    for day in range(1, 31):
        for _ in range(random.randint(2, 5)):
            ts = rand_ts(day, 8, 22)
            # Standard Google/browsing IPs
            ipdr_b.append([msisdn_b, "142.250.76.46", 443, round(random.uniform(10.0, 1000.0), 2), fmt_ts(ts)])
    ipdr_b.sort(key=lambda x: x[4])

    # Headers definition
    cdr_header = ["msisdn_a", "msisdn_b", "imei", "tower_id", "tower_lat", "tower_lon", "call_type", "duration_sec", "timestamp"]
    ipdr_header = ["msisdn", "dest_ip", "dest_port", "data_volume_kb", "timestamp"]

    # Write CSVs
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Kalyan_Chakravarthy.csv"), cdr_header, cdr_a)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_IPDR_Kalyan_Chakravarthy.csv"), ipdr_header, ipdr_a)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Venkatesh_Prasad.csv"), cdr_header, cdr_b)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_IPDR_Venkatesh_Prasad.csv"), ipdr_header, ipdr_b)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Subba_Rao.csv"), cdr_header, cdr_c)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Ananthakrishna.csv"), cdr_header, cdr_d)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Anjali_Devi.csv"), cdr_header, cdr_e)


# ══════════════════════════════════════════════════════════════════════════════
# CASE 2: Hyderabad–Guntur Cyber Fraud Network (Telangana/AP)
# ══════════════════════════════════════════════════════════════════════════════
def gen_case_2():
    print("Generating Case 2...")
    case_prefix = "Case2_Hyd_Gnt_Cyber_Fraud"
    
    # Suspects & contacts
    msisdn_a = "919000888111"  # Ranga Reddy
    msisdn_b = "919177555666"  # Srinivas Rao
    msisdn_c = "919849111222"  # Venkateswara Rao
    msisdn_d = "919955778899"  # Lalitha Prasad (Clean Control)
    handler = "919701000222"   # Bhaskara Rao
    
    contacts_pool = ["919030011223", "919160022334", "919441122334", "919912233445",
                     "918800112233", "917700223344", "919900334455", "919500445566"]

    # ── Suspect A: Ranga Reddy ──
    cdr_a = []
    imei_old = "351111222233334"
    imei_new = "354444555566667"
    
    # Day 1-3: Bursts on HyderabadSecunderabad
    twr_hyd = TOWERS["TWR-HYD-001"]
    
    for day in range(1, 4):
        n_calls = 25 if day <= 2 else 15
        for _ in range(n_calls):
            ts = rand_ts(day, 23, 23) if random.random() < 0.7 else rand_ts(day, 8, 17)
            dest = random.choice([msisdn_b, msisdn_c, handler] + contacts_pool)
            cdr_a.append([msisdn_a, dest, imei_old, "TWR-HYD-001", twr_hyd["lat"], twr_hyd["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])

    # Day 3 Co-location at Hyd Secunderabad at 11:05
    coloc_ts = START_DATE + timedelta(days=2, hours=11, minutes=5)
    cdr_a.append([msisdn_a, msisdn_b, imei_old, "TWR-HYD-001", twr_hyd["lat"], twr_hyd["lon"], "CALL", 180, fmt_ts(coloc_ts)])

    # Day 4: Silent (0 calls)
    
    # Day 5: IMEI swap at 04:15.
    swap_ts = START_DATE + timedelta(days=4, hours=4, minutes=15)
    cdr_a.append([msisdn_a, handler, imei_new, "TWR-HYD-002", TOWERS["TWR-HYD-002"]["lat"], TOWERS["TWR-HYD-002"]["lon"], "CALL", 90, fmt_ts(swap_ts)])
    for _ in range(8):
        ts = rand_ts(5, 5, 23)
        imei = imei_old if ts < swap_ts else imei_new
        dest = random.choice([msisdn_b, handler] + contacts_pool)
        twr = TOWERS["TWR-HYD-002"]
        cdr_a.append([msisdn_a, dest, imei, "TWR-HYD-002", twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])

    # Days 6-30: sparse AP/Telangana movements
    for day in range(6, 31):
        if random.random() < 0.3:
            for _ in range(random.randint(1, 3)):
                ts = rand_ts(day, 23, 23) if random.random() < 0.75 else rand_ts(day, 9, 18)
                dest = random.choice([msisdn_b, handler] + contacts_pool)
                # Travels from Hyderabad -> Guntur -> Vijayawada
                twr_key = random.choice(["TWR-HYD-002", "TWR-GNT-001", "TWR-VJA-001"])
                twr = TOWERS[twr_key]
                cdr_a.append([msisdn_a, dest, imei_new, twr_key, twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])
                
    cdr_a.sort(key=lambda x: x[8])

    # ── Suspect B: Srinivas Rao ──
    cdr_b = []
    imei_b = "352222333344445"
    for day in range(1, 31):
        if day == 3:
            coloc_ts_b = START_DATE + timedelta(days=2, hours=11, minutes=0)
            cdr_b.append([msisdn_b, msisdn_a, imei_b, "TWR-HYD-001", twr_hyd["lat"], twr_hyd["lon"], "CALL", 120, fmt_ts(coloc_ts_b)])
        
        n_calls = random.randint(2, 5)
        for _ in range(n_calls):
            ts = rand_ts(day, 8, 21)
            dest = random.choice([msisdn_a, msisdn_c, handler] + contacts_pool)
            twr = TOWERS["TWR-GNT-001"]
            cdr_b.append([msisdn_b, dest, imei_b, "TWR-GNT-001", twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])
    cdr_b.sort(key=lambda x: x[8])

    # ── Suspect C: Venkateswara Rao ──
    cdr_c = []
    imei_c = "353333444455556"
    for day in range(1, 31):
        if day == 3:
            coloc_ts_c = START_DATE + timedelta(days=2, hours=11, minutes=15)
            cdr_c.append([msisdn_c, msisdn_a, imei_c, "TWR-HYD-001", twr_hyd["lat"], twr_hyd["lon"], "CALL", 150, fmt_ts(coloc_ts_c)])
            
        n_calls = random.randint(1, 3)
        for _ in range(n_calls):
            ts = rand_ts(day, 9, 20)
            dest = random.choice([msisdn_a, msisdn_b, handler] + contacts_pool)
            twr = TOWERS["TWR-VJA-001"]
            cdr_c.append([msisdn_c, dest, imei_c, "TWR-VJA-001", twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])
    cdr_c.sort(key=lambda x: x[8])

    # ── Suspect D: Lalitha Prasad (Clean Control) ──
    cdr_d = []
    imei_d = "355555666677778"
    family_contacts = ["919988112233", "919988445566"]
    for day in range(1, 31):
        n_calls = random.randint(2, 3)
        for _ in range(n_calls):
            ts = rand_ts(day, 9, 19)
            dest = random.choice(family_contacts)
            twr = TOWERS["TWR-HYD-002"]
            cdr_d.append([msisdn_d, dest, imei_d, "TWR-HYD-002", twr["lat"], twr["lon"], "CALL", random.randint(40, 350), fmt_ts(ts)])
    cdr_d.sort(key=lambda x: x[8])

    # ── IPDR Suspect A (WhatsApp/Telegram) ──
    ipdr_a = []
    for day in range(1, 31):
        for _ in range(random.randint(3, 8)):
            ts = rand_ts(day, 0, 23)
            ipdr_a.append([msisdn_a, "157.240.198.35", 443, round(random.uniform(50.0, 4000.0), 2), fmt_ts(ts)])
        for _ in range(random.randint(1, 5)):
            ts = rand_ts(day, 0, 23)
            ipdr_a.append([msisdn_a, "149.154.167.91", 443, round(random.uniform(30.0, 1500.0), 2), fmt_ts(ts)])
    ipdr_a.sort(key=lambda x: x[4])

    # ── IPDR Suspect B ──
    ipdr_b = []
    for day in range(1, 31):
        for _ in range(random.randint(2, 4)):
            ts = rand_ts(day, 9, 21)
            ipdr_b.append([msisdn_b, "142.250.76.46", 443, round(random.uniform(10.0, 800.0), 2), fmt_ts(ts)])
    ipdr_b.sort(key=lambda x: x[4])

    cdr_header = ["msisdn_a", "msisdn_b", "imei", "tower_id", "tower_lat", "tower_lon", "call_type", "duration_sec", "timestamp"]
    ipdr_header = ["msisdn", "dest_ip", "dest_port", "data_volume_kb", "timestamp"]

    # Write CSVs
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Ranga_Reddy.csv"), cdr_header, cdr_a)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_IPDR_Ranga_Reddy.csv"), ipdr_header, ipdr_a)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Srinivas_Rao.csv"), cdr_header, cdr_b)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_IPDR_Srinivas_Rao.csv"), ipdr_header, ipdr_b)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Venkateswara_Rao.csv"), cdr_header, cdr_c)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Lalitha_Prasad.csv"), cdr_header, cdr_d)


# ══════════════════════════════════════════════════════════════════════════════
# CASE 3: Visakhapatnam Port Contraband Ring (Telangana/AP)
# ══════════════════════════════════════════════════════════════════════════════
def gen_case_3():
    print("Generating Case 3...")
    case_prefix = "Case3_Vizag_Contraband_Cartel"
    
    # Suspects & contacts
    msisdn_a = "919849222333"  # Tirupati Naidu
    msisdn_b = "919490111222"  # Madhav Prasad
    msisdn_c = "919160222333"  # Satyanarayana (Clean Control)
    handler = "919611000333"   # Prabhakar Reddy
    
    contacts_pool = ["919010112233", "919440332211", "919866224466", "919959335577",
                     "918121446688", "919703557799", "919177668800", "919052779900"]

    # ── Suspect A: Tirupati Naidu ──
    cdr_a = []
    imei_old = "358888888888888"
    imei_new = "359999999999999"
    
    # Day 1-2: Bursts in Vizag Harbor
    twr_vzg = TOWERS["TWR-VZG-001"]
    
    for day in range(1, 3):
        n_calls = 28
        for _ in range(n_calls):
            ts = rand_ts(day, 23, 23) if random.random() < 0.72 else rand_ts(day, 8, 17)
            dest = random.choice([msisdn_b, handler] + contacts_pool)
            cdr_a.append([msisdn_a, dest, imei_old, "TWR-VZG-001", twr_vzg["lat"], twr_vzg["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])

    # Day 3: Silent (0 calls)
    
    # Day 4: IMEI Swap at 18:30 during travel, co-location with Madhav at Vijayawada Central
    twr_vja = TOWERS["TWR-VJA-001"]
    coloc_ts = START_DATE + timedelta(days=3, hours=18, minutes=35)
    cdr_a.append([msisdn_a, msisdn_b, imei_new, "TWR-VJA-001", twr_vja["lat"], twr_vja["lon"], "CALL", 180, fmt_ts(coloc_ts)])
    
    swap_ts = START_DATE + timedelta(days=3, hours=18, minutes=30)
    for _ in range(7):
        ts = rand_ts(4, 9, 22)
        imei = imei_old if ts < swap_ts else imei_new
        dest = random.choice([msisdn_b, handler] + contacts_pool)
        twr = random.choice([TOWERS["TWR-VZG-001"], TOWERS["TWR-VJA-001"]])
        cdr_a.append([msisdn_a, dest, imei, twr["name"], twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])

    # Days 5-30: sparse AP/Telangana movements
    for day in range(5, 31):
        if random.random() < 0.25:
            for _ in range(random.randint(1, 3)):
                ts = rand_ts(day, 23, 23) if random.random() < 0.8 else rand_ts(day, 10, 16)
                dest = random.choice([msisdn_b, handler] + contacts_pool)
                # Vizag, Kakinada, Rajahmundry
                twr_key = random.choice(["TWR-VZG-001", "TWR-KKD-001", "TWR-RJY-001"])
                twr = TOWERS[twr_key]
                cdr_a.append([msisdn_a, dest, imei_new, twr_key, twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])
                
    cdr_a.sort(key=lambda x: x[8])

    # ── Suspect B: Madhav Prasad ──
    cdr_b = []
    imei_b = "357777777777777"
    for day in range(1, 31):
        if day == 4:
            coloc_ts_b = START_DATE + timedelta(days=3, hours=18, minutes=30)
            cdr_b.append([msisdn_b, msisdn_a, imei_b, "TWR-VJA-001", twr_vja["lat"], twr_vja["lon"], "CALL", 120, fmt_ts(coloc_ts_b)])
        
        n_calls = random.randint(2, 5)
        for _ in range(n_calls):
            ts = rand_ts(day, 8, 21)
            dest = random.choice([msisdn_a, handler] + contacts_pool)
            twr = TOWERS["TWR-KKD-001"]
            cdr_b.append([msisdn_b, dest, imei_b, "TWR-KKD-001", twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])
    cdr_b.sort(key=lambda x: x[8])

    # ── Suspect C: Satyanarayana (Clean Control) ──
    cdr_c = []
    imei_c = "356666666666666"
    family_contacts = ["919494334455", "919494667788"]
    for day in range(1, 31):
        n_calls = random.randint(1, 3)
        for _ in range(n_calls):
            ts = rand_ts(day, 9, 20)
            dest = random.choice(family_contacts)
            twr = TOWERS["TWR-VZG-001"]
            cdr_c.append([msisdn_c, dest, imei_c, "TWR-VZG-001", twr["lat"], twr["lon"], "CALL", random.randint(30, 300), fmt_ts(ts)])
    cdr_c.sort(key=lambda x: x[8])

    # ── IPDR Suspect A (WhatsApp/Telegram) ──
    ipdr_a = []
    for day in range(1, 31):
        for _ in range(random.randint(3, 8)):
            ts = rand_ts(day, 0, 23)
            ipdr_a.append([msisdn_a, "157.240.198.35", 443, round(random.uniform(50.0, 4000.0), 2), fmt_ts(ts)])
        for _ in range(random.randint(1, 5)):
            ts = rand_ts(day, 0, 23)
            ipdr_a.append([msisdn_a, "149.154.167.91", 443, round(random.uniform(30.0, 1500.0), 2), fmt_ts(ts)])
    ipdr_a.sort(key=lambda x: x[4])

    # ── IPDR Suspect B ──
    ipdr_b = []
    for day in range(1, 31):
        for _ in range(random.randint(2, 4)):
            ts = rand_ts(day, 9, 21)
            ipdr_b.append([msisdn_b, "142.250.76.46", 443, round(random.uniform(10.0, 800.0), 2), fmt_ts(ts)])
    ipdr_b.sort(key=lambda x: x[4])

    cdr_header = ["msisdn_a", "msisdn_b", "imei", "tower_id", "tower_lat", "tower_lon", "call_type", "duration_sec", "timestamp"]
    ipdr_header = ["msisdn", "dest_ip", "dest_port", "data_volume_kb", "timestamp"]

    # Write CSVs
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Tirupati_Naidu.csv"), cdr_header, cdr_a)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_IPDR_Tirupati_Naidu.csv"), ipdr_header, ipdr_a)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Madhav_Prasad.csv"), cdr_header, cdr_b)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_IPDR_Madhav_Prasad.csv"), ipdr_header, ipdr_b)
    write_csv(os.path.join(OUT_DIR, f"{case_prefix}_CDR_Satyanarayana.csv"), cdr_header, cdr_c)


if __name__ == "__main__":
    print("Generating three cases for TRACE system...")
    gen_case_1()
    gen_case_2()
    gen_case_3()
    print("Done generating cases!")
