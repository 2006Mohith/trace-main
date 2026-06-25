# -*- coding: utf-8 -*-
"""
End-to-end integration test for TRACE backend.
Runs against SQLite (local dev) - no PostgreSQL required.
"""
import sys
import io
import requests
import time
import os

# Force UTF-8 stdout so symbols work on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_URL = "http://localhost:8000"
SEED_DIR = os.path.join(os.path.dirname(__file__), "seed_csvs")

SUSPECTS = [
    ("Kalyan Chakravarthy", "suspect_a", True),   # has IPDR
    ("Venkatesh Prasad", "suspect_b", False),
    ("Subba Rao", "suspect_c", False),
    ("Ananthakrishna", "suspect_d", False),
    ("Anjali Devi", "suspect_e", False),
]

EXPECTED_EVENTS = {
    "IMEI_SWAP",
    "CO_LOCATION",
    "COMMON_CONTACT",
    "ANOMALY",
    "OTT_USAGE",
}

OK   = "[PASS]"
ERR  = "[FAIL]"
WARN = "[WARN]"


def wait_for_server(retries: int = 20):
    for i in range(retries):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                print(f"{OK} Backend is up at {BASE_URL}")
                return
        except Exception:
            pass
        print(f"   Waiting for backend... ({i+1}/{retries})")
        time.sleep(2)
    print(f"{ERR} Backend did not start in time.")
    sys.exit(1)


def main():
    wait_for_server()

    # ── 1. Create case ────────────────────────────────────────────────────────
    print("\n[1] Creating case...")
    res = requests.post(f"{BASE_URL}/cases", json={"name": "Operation Sandstorm TEST"})
    assert res.status_code == 201, f"Create case failed: {res.text}"
    case = res.json()
    case_id = case["id"]
    print(f"    {OK} Case created: {case_id}")

    # ── 2. Upload suspects ────────────────────────────────────────────────────
    print("\n[2] Uploading suspects...")
    suspect_ids = {}
    for label, filename, has_ipdr in SUSPECTS:
        cdr_path = os.path.join(SEED_DIR, f"{filename}_cdr.csv")
        ipdr_path = os.path.join(SEED_DIR, f"{filename}_ipdr.csv")

        if not os.path.exists(cdr_path):
            print(f"    {WARN} {cdr_path} not found - run seed_data.py first")
            sys.exit(1)

        files = {"cdr_file": open(cdr_path, "rb")}
        if has_ipdr and os.path.exists(ipdr_path):
            files["ipdr_file"] = open(ipdr_path, "rb")

        res = requests.post(
            f"{BASE_URL}/cases/{case_id}/upload",
            data={"suspect_label": label},
            files=files,
        )
        assert res.status_code == 201, f"Upload {label} failed: {res.text}"
        body = res.json()
        suspect_ids[label] = body["suspect_id"]
        cdr_n  = body["rows_inserted_cdr"]
        ipdr_n = body["rows_inserted_ipdr"]
        print(f"    {OK} {label}: {cdr_n} CDR rows, {ipdr_n} IPDR rows")

    # ── 3. Run analysis ───────────────────────────────────────────────────────
    print("\n[3] Running analysis engines...")
    res = requests.post(f"{BASE_URL}/cases/{case_id}/analyze")
    assert res.status_code == 200, f"Analysis failed: {res.text}"
    body = res.json()
    print(f"    {OK} Events generated: {body['events_generated']}")
    print(f"    Summary: {body['summary']}")

    # ── 4. Fetch events ───────────────────────────────────────────────────────
    print("\n[4] Fetching events...")
    res = requests.get(f"{BASE_URL}/cases/{case_id}/events")
    assert res.status_code == 200
    events = res.json()

    print(f"\n{'-'*62}")
    print(f"  EVENTS ({len(events)} total)")
    print(f"{'-'*62}")
    seen_types = set(ev["event_type"] for ev in events)   # scan ALL
    for ev in events[:30]:   # display first 30
        tag = f"[{ev['severity']:6}] {ev['event_type']:20}"
        suspects_str = ", ".join(ev["involved_suspects"])
        print(f"  {tag} | {suspects_str}")
    if len(events) > 30:
        print(f"  ... and {len(events)-30} more")
    print(f"  All detected types: {sorted(seen_types)}")

    # ── 5. Validate event coverage ────────────────────────────────────────────
    print(f"\n[5] Validating event coverage...")
    missing = EXPECTED_EVENTS - seen_types
    if missing:
        print(f"    {WARN} Missing event types: {missing}")
    else:
        print(f"    {OK} All 5 event types detected: {sorted(seen_types)}")

    # ── 6. Network graph ──────────────────────────────────────────────────────
    print("\n[6] Fetching network graph...")
    res = requests.get(f"{BASE_URL}/cases/{case_id}/network")
    assert res.status_code == 200, f"Network failed: {res.text}"
    graph = res.json()
    s_nodes = [n for n in graph["nodes"] if n["node_type"] == "suspect"]
    c_nodes = [n for n in graph["nodes"] if n["node_type"] == "contact"]
    print(f"    {OK} Nodes: {len(s_nodes)} suspects + {len(c_nodes)} contacts | Edges: {len(graph['edges'])}")

    # ── 7. Suspect A profile ──────────────────────────────────────────────────
    print("\n[7] Fetching Kalyan Chakravarthy profile...")
    suspect_a_id = suspect_ids.get("Kalyan Chakravarthy")
    if suspect_a_id:
        res = requests.get(f"{BASE_URL}/suspects/{suspect_a_id}/profile")
        assert res.status_code == 200, f"Profile failed: {res.text}"
        profile = res.json()
        cdr_sum  = profile.get("cdr_summary") or {}
        ipdr_sum = profile.get("ipdr_summary") or {}
        print(f"    {OK} Calls: {cdr_sum.get('total_calls','?')}  "
              f"Contacts: {cdr_sum.get('unique_contacts','?')}  "
              f"Burst: {cdr_sum.get('burst_score','?')}")
        if ipdr_sum:
            apps = [r["app"] for r in ipdr_sum.get("ott_breakdown", [])]
            print(f"    {OK} OTT apps: {apps}")
        mov = profile.get("movement_data", [])
        coloc = [m for m in mov if m.get("co_location")]
        print(f"    {OK} Movement towers: {len(mov)}  Co-location hits: {len(coloc)}")

    # ── 8. PDF report ─────────────────────────────────────────────────────────
    print("\n[8] PDF report generation...")
    if suspect_a_id:
        res = requests.get(f"{BASE_URL}/suspects/{suspect_a_id}/report.pdf")
        assert res.status_code == 200, f"Report failed: {res.text}"
        ct = res.headers.get("content-type", "")
        assert ct.startswith("application/pdf"), f"Expected PDF, got: {ct}"
        print(f"    {OK} PDF size: {len(res.content)/1024:.1f} KB")

    # ── Final result ──────────────────────────────────────────────────────────
    print(f"\n{'='*62}")
    if missing:
        print(f"  {WARN} PARTIAL PASS - missing event types: {missing}")
        sys.exit(1)
    else:
        print(f"  {OK} ALL TESTS PASSED - TRACE backend fully operational")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
