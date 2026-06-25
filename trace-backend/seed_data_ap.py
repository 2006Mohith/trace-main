"""
seed_data_ap.py — Operation Godavari scenario (Prakasham District, AP/Telangana)
Generates 30 days of CDR + IPDR data for 5 suspects and 1 handler.

Usage:
    python seed_data_ap.py
"""

import csv
import os
import random
from datetime import datetime, timedelta

# STRICT GEOGRAPHIC BOUNDS — all towers MUST be within this bounding box
# Andhra Pradesh + Telangana bounding box:
# Lat: 12.6 to 19.9 (south to north)
# Lon: 76.7 to 84.8 (west to east)
# DO NOT generate any coordinate outside this box.

TOWERS = [
    # Prakasham District (primary jurisdiction)
    {"id": "TWR-ONG-001", "name": "Ongole Central",     "lat": 15.5057, "lon": 80.0499, "district": "Prakasham"},
    {"id": "TWR-ONG-002", "name": "Ongole East",        "lat": 15.5120, "lon": 80.0620, "district": "Prakasham"},
    {"id": "TWR-MRT-001", "name": "Markapur",           "lat": 15.7333, "lon": 79.2667, "district": "Prakasham"},
    {"id": "TWR-CDD-001", "name": "Chirala",            "lat": 15.8167, "lon": 80.3500, "district": "Prakasham"},
    {"id": "TWR-KAN-001", "name": "Kandukur",           "lat": 15.2167, "lon": 79.9000, "district": "Prakasham"},
    # Neighboring AP districts
    {"id": "TWR-GNT-001", "name": "Guntur Junction",   "lat": 16.3067, "lon": 80.4365, "district": "Guntur"},
    {"id": "TWR-VJA-001", "name": "Vijayawada Central","lat": 16.5062, "lon": 80.6480, "district": "Krishna"},
    {"id": "TWR-NLR-001", "name": "Nellore Town",      "lat": 14.4426, "lon": 79.9865, "district": "Nellore"},
    # Telangana (bordering)
    {"id": "TWR-HYD-001", "name": "Hyderabad Secunderabad","lat": 17.4399, "lon": 78.4983, "district": "Hyderabad"},
    {"id": "TWR-HYD-002", "name": "LB Nagar",          "lat": 17.3453, "lon": 78.5479, "district": "Hyderabad"},
]

TOWER_MAP = {t["id"]: t for t in TOWERS}

# VALIDATION — add this check before writing any CSV row:
def validate_coord(lat, lon):
    assert 12.6 <= lat <= 19.9, f"Lat {lat} outside AP/Telangana bounds"
    assert 76.7 <= lon <= 84.8, f"Lon {lon} outside AP/Telangana bounds"
    return True

# ── Suspect Registry ──────────────────────────────────────────────────────────
SUSPECTS = [
    {"label": "Kalyan Chakravarthy", "msisdn": "919440123456", "role": "kingpin"},
    {"label": "Venkatesh Prasad", "msisdn": "919963987654", "role": "distributor"},
    {"label": "Subba Rao", "msisdn": "919849000312", "role": "distributor"},
    {"label": "Ananthakrishna", "msisdn": "919000100004", "role": "buyer"},
    {"label": "Anjali Devi", "msisdn": "919848011223", "role": "clean"},
]
HANDLER_NUMBER = "919888000111"  # common coordinator

# IMEI pool per suspect
IMEI_POOL = {
    "919440123456": ["359876123400001", "490876123499999"],  # A swaps on Day 3
    "919963987654": ["352098765432100"],
    "919849000312": ["356001122334455"],
    "919000100004": ["351234567890004"],
    "919848011223": ["351234567890005"],
}

# Family numbers (for Suspect E — fully clean calls)
FAMILY_NUMBERS = [
    "919177001001", "919177001002", "919177001003",
]

START_DATE = datetime(2026, 6, 1, 0, 0, 0)

random.seed(42)  # reproducible


def rand_ts(day: int, hour_min: int = 0, hour_max: int = 23) -> datetime:
    """Random timestamp within a day, within hour bounds."""
    base = START_DATE + timedelta(days=day - 1)
    h = random.randint(hour_min, hour_max)
    m = random.randint(0, 59)
    s = random.randint(0, 59)
    return base.replace(hour=h, minute=m, second=s)


def fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# Movement routes — realistic NH-16 drug route corridor
SUSPECT_ROUTES = {
    'Kalyan Chakravarthy': ['TWR-ONG-001', 'TWR-ONG-002', 'TWR-CDD-001', 'TWR-ONG-001', 'TWR-MRT-001'],
    'Venkatesh Prasad': ['TWR-ONG-001', 'TWR-GNT-001', 'TWR-VJA-001', 'TWR-GNT-001'],
    'Subba Rao': ['TWR-HYD-001', 'TWR-HYD-002', 'TWR-ONG-002', 'TWR-HYD-001'],
    'Ananthakrishna': ['TWR-NLR-001', 'TWR-KAN-001', 'TWR-NLR-001'],
    'Anjali Devi': ['TWR-ONG-001', 'TWR-ONG-001'],  # stays local, clean
}

def tower_for(suspect_msisdn: str, day: int) -> dict:
    """Return the tower a suspect is at on a given day, based on the story."""
    msisdn_to_label = {
        "919440123456": "Kalyan Chakravarthy",
        "919963987654": "Venkatesh Prasad",
        "919849000312": "Subba Rao",
        "919000100004": "Ananthakrishna",
        "919848011223": "Anjali Devi",
    }
    label = msisdn_to_label.get(suspect_msisdn, "Anjali Devi")
    route = SUSPECT_ROUTES[label]
    idx = min((day - 1) // 7, len(route) - 1)
    tower_id = route[idx]
    return TOWER_MAP[tower_id]


# ── CDR Generation ────────────────────────────────────────────────────────────

CDR_HEADER = [
    "msisdn_a", "msisdn_b", "imei", "tower_id", "tower_lat", "tower_lon",
    "call_type", "duration_sec", "timestamp",
]


def generate_cdr_a() -> list[list]:
    """Kalyan Chakravarthy: burst on Days 1-2, IMEI swap on Day 3, silent on Day 4."""
    rows = []
    targets = [s["msisdn"] for s in SUSPECTS if s["msisdn"] != "919440123456"] + [HANDLER_NUMBER]

    for day in range(1, 31):
        tower = tower_for("919440123456", day)
        # IMEI: swap on Day 3 at 02:30
        if day < 3:
            imei = IMEI_POOL["919440123456"][0]
        else:
            imei = IMEI_POOL["919440123456"][1]

        # Silent on Day 4
        if day == 4:
            continue

        # Burst in Days 1-2: 22 calls/day; Day 3: 10 calls; Days 5-30: 3 calls/day
        if day <= 2:
            n_calls = 22
        elif day == 3:
            n_calls = 10
        else:
            n_calls = random.randint(2, 4)

        for _ in range(n_calls):
            # Night call ratio >70%
            if random.random() < 0.72:
                ts = rand_ts(day, 23, 23) if random.random() < 0.5 else rand_ts(day, 0, 4)
            else:
                ts = rand_ts(day, 6, 20)

            # Ensure IMEI swap timing on Day 3
            if day == 3:
                swap_time = START_DATE + timedelta(days=2, hours=2, minutes=30)
                imei = IMEI_POOL["919440123456"][1] if ts >= swap_time else IMEI_POOL["919440123456"][0]

            msisdn_b = random.choice(targets)
            dur = random.randint(30, 420)

            rows.append([
                "919440123456", msisdn_b, imei, tower["id"], tower["lat"], tower["lon"],
                "CALL", dur, fmt_ts(ts),
            ])

        # Add some SMS
        for _ in range(random.randint(2, 4)):
            ts = rand_ts(day)
            if day == 3:
                swap_time = START_DATE + timedelta(days=2, hours=2, minutes=30)
                imei = IMEI_POOL["919440123456"][1] if ts >= swap_time else IMEI_POOL["919440123456"][0]
            rows.append([
                "919440123456", random.choice(targets), imei, tower["id"], tower["lat"], tower["lon"],
                "SMS", 0, fmt_ts(ts),
            ])

    return rows


def generate_cdr_b() -> list[list]:
    """Venkatesh Prasad: distributor: co-location with Kalyan on Day 2 15:00 at TWR-CDD-001."""
    rows = []
    targets_b = ["919440123456", "919849000312", HANDLER_NUMBER]
    imei = IMEI_POOL["919963987654"][0]

    for day in range(1, 31):
        tower = tower_for("919963987654", day)
        n_calls = random.randint(4, 8)

        for _ in range(n_calls):
            ts = rand_ts(day)
            msisdn_b = random.choice(targets_b)
            rows.append([
                "919963987654", msisdn_b, imei, tower["id"], tower["lat"], tower["lon"],
                "CALL", random.randint(20, 360), fmt_ts(ts),
            ])

        # Day 2 15:00 — at TWR-CDD-001 (Chirala), call Kalyan
        if day == 2:
            co_ts = START_DATE + timedelta(days=1, hours=15, minutes=0)
            tower = TOWER_MAP["TWR-CDD-001"]
            rows.append([
                "919963987654", "919440123456", imei, "TWR-CDD-001", tower["lat"], tower["lon"],
                "CALL", 180, fmt_ts(co_ts),
            ])

    return rows


def generate_cdr_c() -> list[list]:
    """Subba Rao: co-location at TWR-CDD-001 Day 2 15:15."""
    rows = []
    targets_c = ["919440123456", "919963987654", HANDLER_NUMBER]
    imei = IMEI_POOL["919849000312"][0]

    for day in range(1, 31):
        tower = tower_for("919849000312", day)
        n_calls = random.randint(3, 7)

        for _ in range(n_calls):
            ts = rand_ts(day)
            msisdn_b = random.choice(targets_c)
            rows.append([
                "919849000312", msisdn_b, imei, tower["id"], tower["lat"], tower["lon"],
                "CALL", random.randint(15, 300), fmt_ts(ts),
            ])

        # Day 2 15:15 — at TWR-CDD-001 (co-location)
        if day == 2:
            co_ts = START_DATE + timedelta(days=1, hours=15, minutes=15)
            tower = TOWER_MAP["TWR-CDD-001"]
            rows.append([
                "919849000312", "919440123456", imei, "TWR-CDD-001", tower["lat"], tower["lon"],
                "CALL", 240, fmt_ts(co_ts),
            ])

    return rows


def generate_cdr_d() -> list[list]:
    """Ananthakrishna: calls B and C, stays in Nellore."""
    rows = []
    targets_d = ["919963987654", "919849000312"]
    imei = IMEI_POOL["919000100004"][0]

    for day in range(1, 31):
        tower = tower_for("919000100004", day)
        n_calls = random.randint(1, 3)
        for _ in range(n_calls):
            ts = rand_ts(day, 8, 20)
            msisdn_b = random.choice(targets_d)
            rows.append([
                "919000100004", msisdn_b, imei, tower["id"], tower["lat"], tower["lon"],
                "CALL", random.randint(30, 180), fmt_ts(ts),
            ])

    return rows


def generate_cdr_e() -> list[list]:
    """Anjali Devi: clean, only calls family."""
    rows = []
    imei = IMEI_POOL["919848011223"][0]

    for day in range(1, 31):
        tower = tower_for("919848011223", day)
        n_calls = random.randint(2, 5)
        for _ in range(n_calls):
            ts = rand_ts(day, 7, 22)
            msisdn_b = random.choice(FAMILY_NUMBERS)
            rows.append([
                "919848011223", msisdn_b, imei, tower["id"], tower["lat"], tower["lon"],
                "CALL", random.randint(20, 600), fmt_ts(ts),
            ])

    return rows


# ── IPDR Generation ───────────────────────────────────────────────────────────

IPDR_HEADER = [
    "msisdn", "dest_ip", "dest_port", "data_volume_kb", "timestamp"
]

OTT_APPS = [
    ("WhatsApp", "157.240.198.35", 443),
    ("Telegram", "149.154.167.91", 443),
]


def generate_ipdr(msisdn: str, days: int = 30, sessions_per_day: int = 14) -> list[list]:
    rows = []
    for day in range(1, days + 1):
        n_sessions = random.randint(sessions_per_day // 2, sessions_per_day)
        for _ in range(n_sessions):
            ts = rand_ts(day)
            app = random.choice(OTT_APPS)
            volume = round(random.uniform(10, 2500), 1)
            rows.append([
                msisdn, app[1], app[2], volume, fmt_ts(ts)
            ])
    return rows


# ── Write CSVs ────────────────────────────────────────────────────────────────

def write_csv(path: str, header: list, rows: list):
    # Validate coordinates
    lat_idx = header.index("tower_lat") if "tower_lat" in header else -1
    lon_idx = header.index("tower_lon") if "tower_lon" in header else -1
        
    for r in rows:
        if lat_idx != -1 and lon_idx != -1:
            lat = float(r[lat_idx])
            lon = float(r[lon_idx])
            validate_coord(lat, lon)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  Written {len(rows):>4} rows -> {path}")


if __name__ == "__main__":
    print("Generating seed data: Operation Godavari scenario (AP/Telangana)...")

    # Outputs for data/
    write_csv("data/cdr_suspectA.csv", CDR_HEADER, generate_cdr_a())
    write_csv("data/cdr_suspectB.csv", CDR_HEADER, generate_cdr_b())
    write_csv("data/cdr_suspectC.csv", CDR_HEADER, generate_cdr_c())
    write_csv("data/cdr_suspectD.csv", CDR_HEADER, generate_cdr_d())
    write_csv("data/cdr_suspectE.csv", CDR_HEADER, generate_cdr_e())

    write_csv("data/ipdr_suspectA.csv", IPDR_HEADER, generate_ipdr("919440123456", sessions_per_day=14))
    write_csv("data/ipdr_suspectB.csv", IPDR_HEADER, generate_ipdr("919963987654", sessions_per_day=10))

    # Outputs for seed_csvs/ (overwrite so tests/UI use correct AP data)
    write_csv("seed_csvs/suspect_a_cdr.csv", CDR_HEADER, generate_cdr_a())
    write_csv("seed_csvs/suspect_b_cdr.csv", CDR_HEADER, generate_cdr_b())
    write_csv("seed_csvs/suspect_c_cdr.csv", CDR_HEADER, generate_cdr_c())
    write_csv("seed_csvs/suspect_d_cdr.csv", CDR_HEADER, generate_cdr_d())
    write_csv("seed_csvs/suspect_e_cdr.csv", CDR_HEADER, generate_cdr_e())

    write_csv("seed_csvs/suspect_a_ipdr.csv", IPDR_HEADER, generate_ipdr("919440123456", sessions_per_day=14))
    write_csv("seed_csvs/suspect_b_ipdr.csv", IPDR_HEADER, generate_ipdr("919963987654", sessions_per_day=10))

    print("\nSeed data generated: Operation Godavari scenario (AP/Telangana)")
    print("Case: Operation Godavari - Prakasham District")
    print("Towers: 10 AP/Telangana locations (Ongole, Guntur, Vijayawada, Hyderabad, Nellore...)")
    print("Story: Kalyan Chakravarthy (kingpin/Ongole) -> Venkatesh Prasad (distributor) -> Subba Rao")
    print("       Co-location event: TWR-CDD-001 (Chirala) on Day 2 at 15:00-15:30")
    print("       IMEI swap: Kalyan Chakravarthy on Day 3 at ~02:30")
    print("       Handler: 919888000111 appears in Kalyan, Venkatesh, Subba Rao CDR only")
