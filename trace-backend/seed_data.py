"""
Seed Data Generator — Operation Sandstorm
Generates synthetic CDR and IPDR CSV files for the TRACE demo scenario.

Run: python seed_data.py
Outputs: seed_csvs/ directory with CDR and IPDR files per suspect.
"""
import os
import random
import csv
from datetime import datetime, timedelta

random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "seed_csvs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Scenario constants ──────────────────────────────────────────────────────────
START_DATE = datetime(2024, 1, 1, 0, 0, 0)
NUM_DAYS = 30
HANDLER_NUMBER = "+919999000001"

SUSPECTS = {
    "Suspect A": {"msisdn": "+919000000001", "imei_before": "IMEI-A1", "imei_after": "IMEI-A2", "swap_day": 3},
    "Suspect B": {"msisdn": "+919000000002", "imei": "IMEI-B1"},
    "Suspect C": {"msisdn": "+919000000003", "imei": "IMEI-C1"},
    "Suspect D": {"msisdn": "+919000000004", "imei": "IMEI-D1"},
    "Suspect E": {"msisdn": "+919000000005", "imei": "IMEI-E1"},
}

# Tower definitions
TOWERS = {
    "Tower-T01": (12.9716, 77.5946),
    "Tower-T02": (13.0827, 80.2707),
    "Tower-T03": (17.3850, 78.4867),
    "Tower-T04": (19.0760, 72.8777),
    "Tower-T05": (28.7041, 77.1025),
    "Tower-T06": (12.2958, 76.6394),
    "Tower-T07": (15.8497, 74.4977),
    "Tower-T08": (11.0168, 76.9558),
    "Tower-T09": (16.5062, 80.6480),
    "Tower-T10": (22.5726, 88.3639),
    "Tower-T14": (13.0550, 80.2100),  # Meeting tower
}

TOWER_IDS = list(TOWERS.keys())

# WhatsApp / Meta IP ranges
WHATSAPP_IPS = [f"157.240.{r}.{c}" for r in range(1, 20) for c in range(1, 5)]
# Telegram IP ranges
TELEGRAM_IPS = [f"149.154.{r}.{c}" for r in range(160, 175) for c in range(1, 5)]
# Standard browsing IPs
STANDARD_IPS = [f"103.{r}.{c}.1" for r in range(10, 50) for c in range(1, 5)]


def rand_ts(day_offset, hour_min=8, hour_max=22, date_base=START_DATE):
    """Generate a random timestamp on a given day."""
    day = date_base + timedelta(days=day_offset)
    hour = random.randint(hour_min, hour_max)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return day.replace(hour=hour, minute=minute, second=second)


def night_ts(day_offset, date_base=START_DATE):
    """Generate a night-time timestamp."""
    day = date_base + timedelta(days=day_offset)
    hour = random.choice([23, 0, 1, 2, 3, 4])
    if hour == 23:
        pass
    else:
        day = day + timedelta(days=1)
    return day.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))


def write_csv(filename, rows, headers):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Written: {path} ({len(rows)} rows)")
    return path


# ── CDR Headers ────────────────────────────────────────────────────────────────
CDR_HEADERS = ["msisdn_a", "msisdn_b", "imei", "tower_id", "tower_lat", "tower_lon",
               "call_type", "duration_sec", "timestamp"]
IPDR_HEADERS = ["msisdn", "dest_ip", "dest_port", "data_volume_kb", "timestamp"]


def make_cdr_row(msisdn_a, msisdn_b, imei, tower_id, call_type, duration_sec, ts):
    lat, lon = TOWERS[tower_id]
    return {
        "msisdn_a": msisdn_a,
        "msisdn_b": msisdn_b,
        "imei": imei,
        "tower_id": tower_id,
        "tower_lat": lat,
        "tower_lon": lon,
        "call_type": call_type,
        "duration_sec": duration_sec,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
    }


def make_ipdr_row(msisdn, dest_ip, dest_port, data_kb, ts):
    return {
        "msisdn": msisdn,
        "dest_ip": dest_ip,
        "dest_port": dest_port,
        "data_volume_kb": round(data_kb, 2),
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# SUSPECT A — Kingpin
# ══════════════════════════════════════════════════════════════════════════════
def generate_suspect_a():
    rows = []
    msisdn = SUSPECTS["Suspect A"]["msisdn"]
    imei1 = SUSPECTS["Suspect A"]["imei_before"]
    imei2 = SUSPECTS["Suspect A"]["imei_after"]
    swap_day = SUSPECTS["Suspect A"]["swap_day"]

    others = [
        SUSPECTS["Suspect B"]["msisdn"],
        SUSPECTS["Suspect C"]["msisdn"],
        SUSPECTS["Suspect D"]["msisdn"],
        HANDLER_NUMBER,
        "+919000100001", "+919000100002",
    ]

    # Days 1-2: burst — 60+ calls
    for day in range(0, 2):
        imei = imei1
        for _ in range(32):
            ts = rand_ts(day, 8, 22)
            target = random.choice(others)
            rows.append(make_cdr_row(msisdn, target, imei, random.choice(TOWER_IDS),
                                      "CALL", random.randint(30, 600), ts))
        # Night calls (high ratio)
        for _ in range(6):
            ts = night_ts(day)
            rows.append(make_cdr_row(msisdn, random.choice(others), imei,
                                      random.choice(TOWER_IDS), "CALL", random.randint(60, 300), ts))

    # Day 3: IMEI swap — first few calls IMEI-A1, then IMEI-A2
    for i in range(3):
        ts = rand_ts(2, 8, 10)
        rows.append(make_cdr_row(msisdn, random.choice(others), imei1, "Tower-T01", "CALL", 120, ts))
    swap_ts = rand_ts(swap_day - 1, 11, 12)
    for i in range(4):
        ts = rand_ts(2, 13, 22)
        rows.append(make_cdr_row(msisdn, random.choice(others), imei2, random.choice(TOWER_IDS),
                                  "CALL", random.randint(30, 300), ts))

    # Day 2 (index 1) at 14:15 on Tower-T14 — meeting
    meeting_ts = (START_DATE + timedelta(days=1)).replace(hour=14, minute=15, second=0)
    rows.append(make_cdr_row(msisdn, SUSPECTS["Suspect B"]["msisdn"], imei1, "Tower-T14",
                              "CALL", 180, meeting_ts))

    # Days 4-30: go silent (very few calls)
    for day in range(3, NUM_DAYS):
        if random.random() < 0.15:  # only 15% chance of any call
            ts = rand_ts(day, 9, 17)
            rows.append(make_cdr_row(msisdn, random.choice(others), imei2,
                                      random.choice(TOWER_IDS), "CALL", random.randint(30, 120), ts))

    # SMS rows
    for day in range(0, 5):
        for _ in range(random.randint(2, 5)):
            ts = rand_ts(day, 8, 21)
            rows.append(make_cdr_row(msisdn, random.choice(others), imei1 if day < swap_day else imei2,
                                      random.choice(TOWER_IDS), "SMS", 0, ts))

    # Handler contact — appears in A, B, C CDRs
    for day in range(0, 10):
        ts = rand_ts(day, 10, 18)
        rows.append(make_cdr_row(msisdn, HANDLER_NUMBER, imei1 if day < swap_day else imei2,
                                  random.choice(TOWER_IDS), "CALL", random.randint(60, 400), ts))

    rows.sort(key=lambda r: r["timestamp"])
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# SUSPECT B — Distributor 1
# ══════════════════════════════════════════════════════════════════════════════
def generate_suspect_b():
    rows = []
    msisdn = SUSPECTS["Suspect B"]["msisdn"]
    imei = SUSPECTS["Suspect B"]["imei"]
    others = [SUSPECTS["Suspect A"]["msisdn"], SUSPECTS["Suspect C"]["msisdn"],
              SUSPECTS["Suspect D"]["msisdn"], HANDLER_NUMBER]

    for day in range(NUM_DAYS):
        for _ in range(random.randint(3, 8)):
            ts = rand_ts(day, 8, 21)
            target = random.choice(others)
            rows.append(make_cdr_row(msisdn, target, imei, random.choice(TOWER_IDS),
                                      "CALL", random.randint(30, 400), ts))

    # Day 2 14:00-14:30 on Tower-T14 (meeting)
    for minute in [0, 10, 20]:
        ts = (START_DATE + timedelta(days=1)).replace(hour=14, minute=minute, second=0)
        rows.append(make_cdr_row(msisdn, SUSPECTS["Suspect C"]["msisdn"], imei, "Tower-T14",
                                  "CALL", 120, ts))

    # Handler calls
    for day in range(0, 12):
        ts = rand_ts(day, 9, 18)
        rows.append(make_cdr_row(msisdn, HANDLER_NUMBER, imei, random.choice(TOWER_IDS),
                                  "CALL", random.randint(60, 300), ts))

    rows.sort(key=lambda r: r["timestamp"])
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# SUSPECT C — Distributor 2
# ══════════════════════════════════════════════════════════════════════════════
def generate_suspect_c():
    rows = []
    msisdn = SUSPECTS["Suspect C"]["msisdn"]
    imei = SUSPECTS["Suspect C"]["imei"]
    others = [SUSPECTS["Suspect A"]["msisdn"], SUSPECTS["Suspect B"]["msisdn"],
              SUSPECTS["Suspect D"]["msisdn"], HANDLER_NUMBER]

    for day in range(NUM_DAYS):
        for _ in range(random.randint(3, 7)):
            ts = rand_ts(day, 8, 21)
            target = random.choice(others)
            rows.append(make_cdr_row(msisdn, target, imei, random.choice(TOWER_IDS),
                                      "CALL", random.randint(30, 350), ts))

    # Day 2 14:00-14:30 on Tower-T14 (meeting)
    for minute in [5, 15, 25]:
        ts = (START_DATE + timedelta(days=1)).replace(hour=14, minute=minute, second=0)
        rows.append(make_cdr_row(msisdn, SUSPECTS["Suspect B"]["msisdn"], imei, "Tower-T14",
                                  "CALL", 90, ts))

    # Handler calls
    for day in range(0, 10):
        ts = rand_ts(day, 10, 17)
        rows.append(make_cdr_row(msisdn, HANDLER_NUMBER, imei, random.choice(TOWER_IDS),
                                  "CALL", random.randint(60, 280), ts))

    rows.sort(key=lambda r: r["timestamp"])
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# SUSPECT D — Buyer (normal, no anomaly)
# ══════════════════════════════════════════════════════════════════════════════
def generate_suspect_d():
    rows = []
    msisdn = SUSPECTS["Suspect D"]["msisdn"]
    imei = SUSPECTS["Suspect D"]["imei"]
    others = [SUSPECTS["Suspect B"]["msisdn"], SUSPECTS["Suspect C"]["msisdn"]]

    for day in range(NUM_DAYS):
        for _ in range(random.randint(2, 5)):
            ts = rand_ts(day, 9, 20)
            target = random.choice(others)
            rows.append(make_cdr_row(msisdn, target, imei, random.choice(TOWER_IDS),
                                      "CALL", random.randint(30, 300), ts))

    rows.sort(key=lambda r: r["timestamp"])
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# SUSPECT E — Completely clean
# ══════════════════════════════════════════════════════════════════════════════
def generate_suspect_e():
    rows = []
    msisdn = SUSPECTS["Suspect E"]["msisdn"]
    imei = SUSPECTS["Suspect E"]["imei"]
    clean_contacts = [f"+918800{i:06d}" for i in range(1, 8)]

    for day in range(NUM_DAYS):
        for _ in range(random.randint(2, 4)):
            ts = rand_ts(day, 8, 20)
            target = random.choice(clean_contacts)
            rows.append(make_cdr_row(msisdn, target, imei, random.choice(TOWER_IDS),
                                      "CALL", random.randint(60, 500), ts))

    rows.sort(key=lambda r: r["timestamp"])
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# IPDR — Suspect A: WhatsApp + Telegram
# ══════════════════════════════════════════════════════════════════════════════
def generate_ipdr_a():
    rows = []
    msisdn = SUSPECTS["Suspect A"]["msisdn"]
    for day in range(NUM_DAYS):
        for _ in range(random.randint(3, 8)):
            ip = random.choice(WHATSAPP_IPS)
            ts = rand_ts(day, 8, 23)
            rows.append(make_ipdr_row(msisdn, ip, 443, random.uniform(50, 5000), ts))
        for _ in range(random.randint(2, 5)):
            ip = random.choice(TELEGRAM_IPS)
            ts = rand_ts(day, 9, 22)
            rows.append(make_ipdr_row(msisdn, ip, 443, random.uniform(30, 2000), ts))
    rows.sort(key=lambda r: r["timestamp"])
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# IPDR — Suspect B: standard browsing only
# ══════════════════════════════════════════════════════════════════════════════
def generate_ipdr_b():
    rows = []
    msisdn = SUSPECTS["Suspect B"]["msisdn"]
    for day in range(NUM_DAYS):
        for _ in range(random.randint(2, 6)):
            ip = random.choice(STANDARD_IPS)
            ts = rand_ts(day, 8, 21)
            rows.append(make_ipdr_row(msisdn, ip, random.choice([80, 443, 8080]),
                                       random.uniform(10, 1000), ts))
    rows.sort(key=lambda r: r["timestamp"])
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating Operation Sandstorm seed data...")
    print()

    # CDR files
    cdr_a = generate_suspect_a()
    cdr_b = generate_suspect_b()
    cdr_c = generate_suspect_c()
    cdr_d = generate_suspect_d()
    cdr_e = generate_suspect_e()

    write_csv("suspect_a_cdr.csv", cdr_a, CDR_HEADERS)
    write_csv("suspect_b_cdr.csv", cdr_b, CDR_HEADERS)
    write_csv("suspect_c_cdr.csv", cdr_c, CDR_HEADERS)
    write_csv("suspect_d_cdr.csv", cdr_d, CDR_HEADERS)
    write_csv("suspect_e_cdr.csv", cdr_e, CDR_HEADERS)

    total_cdr = len(cdr_a) + len(cdr_b) + len(cdr_c) + len(cdr_d) + len(cdr_e)
    print(f"\n  Total CDR rows: {total_cdr}")

    # IPDR files
    ipdr_a = generate_ipdr_a()
    ipdr_b = generate_ipdr_b()

    write_csv("suspect_a_ipdr.csv", ipdr_a, IPDR_HEADERS)
    write_csv("suspect_b_ipdr.csv", ipdr_b, IPDR_HEADERS)

    total_ipdr = len(ipdr_a) + len(ipdr_b)
    print(f"  Total IPDR rows: {total_ipdr}")

    print()
    print("Scenario: Operation Sandstorm")
    print("  Suspect A: IMEI swap on Day 3, burst on Days 1-2, WhatsApp+Telegram IPDR")
    print("  Suspects A,B,C: Co-location at Tower-T14 on Day 2 at 14:00-14:30")
    print("  Handler number: +919999000001 — appears in A, B, C CDRs")
    print("  Suspect D: clean, calls B and C only")
    print("  Suspect E: completely clean, no shared contacts")
    print()
    print(f"Output directory: {OUTPUT_DIR}")
    print("Done.")
