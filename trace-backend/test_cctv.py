# -*- coding: utf-8 -*-
"""
CCTV Surveillance & Facial Recognition Integration Test.
"""
import sys
import requests
import os
import time

BASE_URL = "http://127.0.0.1:8000"
TEST_FACE_PATH = "test_face.png"

def wait_for_server(retries: int = 20):
    for i in range(retries):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                print(f"[PASS] Backend is up at {BASE_URL}")
                return
        except Exception:
            pass
        print(f"   Waiting for backend... ({i+1}/{retries})")
        time.sleep(2)
    print("[FAIL] Backend did not start in time.")
    sys.exit(1)

def test_cctv_pipeline():
    wait_for_server()
    if not os.path.exists(TEST_FACE_PATH):
        print(f"[FAIL] Test face image '{TEST_FACE_PATH}' not found. Please place it in the directory.")
        sys.exit(1)

    import sqlite3
    import shutil
    db_path = "trace.db"
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cctv_face_entries")
            cursor.execute("DELETE FROM cctv_sightings")
            conn.commit()
            conn.close()
            print("[INFO] Cleaned up existing cctv_face_entries and cctv_sightings database records.")
        except Exception as e:
            print(f"[WARN] Database cleanup warning: {e}")
            
    registry_path = os.path.join("storage", "face_registry")
    if os.path.exists(registry_path):
        try:
            shutil.rmtree(registry_path)
            print("[INFO] Cleaned up storage/face_registry directory.")
        except Exception as e:
            print(f"[WARN] Face registry folder cleanup warning: {e}")
        
    print("\n" + "="*50)
    print("RUNNING CCTV ENGINE & API ROUTE INTEGRATION TESTS")
    print("="*50)

    # 1. Create a Case
    print("\n[1] Creating a test case...")
    res = requests.post(f"{BASE_URL}/cases", json={"name": "CCTV Surveillance Evaluation"})
    assert res.status_code == 201, f"Case creation failed: {res.text}"
    case = res.json()
    case_id = case["id"]
    print(f"    [PASS] Case created with ID: {case_id}")

    # 2. Upload a suspect and populate their details
    print("\n[2] Registering suspect 'Kalyan Chakravarthy'...")
    cdr_path = os.path.join("seed_csvs", "suspect_a_cdr.csv")
    files = {"cdr_file": open(cdr_path, "rb")}
    res = requests.post(
        f"{BASE_URL}/cases/{case_id}/upload",
        data={"suspect_label": "Kalyan Chakravarthy"},
        files=files
    )
    assert res.status_code == 201, f"Suspect upload failed: {res.text}"
    suspect_id = res.json()["suspect_id"]
    print(f"    [PASS] Suspect registered with ID: {suspect_id}")

    # 3. Create a CCTV Camera
    print("\n[3] Registering a CCTV Camera...")
    import random
    cam_id = f"ONG-CAM-{random.randint(100, 99999)}"
    camera_payload = {
        "camera_id": cam_id,
        "location_name": "Ongole Bus Stand Main Terminal",
        "latitude": 15.5056,
        "longitude": 80.0494,
        "rtsp_url": "rtsp://admin:pass123@192.168.1.101:554/live"
    }
    res = requests.post(f"{BASE_URL}/cctv/cameras", json=camera_payload)
    assert res.status_code == 201, f"Camera registration failed: {res.text}"
    print(f"    [PASS] Camera '{cam_id}' registered successfully.")

    # 4. Get list of CCTV cameras
    print("\n[4] Querying CCTV cameras status list...")
    res = requests.get(f"{BASE_URL}/cctv/cameras")
    assert res.status_code == 200, f"Cameras query failed: {res.text}"
    cameras = res.json()
    assert len(cameras) > 0, "No cameras returned"
    print(f"    [PASS] Returned {len(cameras)} registered cameras: {cameras}")

    # 5. Register suspect face photo in the registry
    print("\n[5] Registering suspect face image to the database...")
    face_file = {"file": open(TEST_FACE_PATH, "rb")}
    res = requests.post(f"{BASE_URL}/cctv/register-face/{suspect_id}", files=face_file)
    assert res.status_code == 201, f"Face registration failed: {res.text}"
    reg_res = res.json()
    face_id = reg_res["face_id"]
    quality_score = reg_res["quality_score"]
    print(f"    [PASS] Face registered. ID: {face_id} | Quality Score: {quality_score}")

    # 6. Query suspect face quality scores
    print("\n[6] Fetching suspect registered face quality overview...")
    res = requests.get(f"{BASE_URL}/cctv/suspect/{suspect_id}/face-quality")
    assert res.status_code == 200, f"Face quality query failed: {res.text}"
    quality_records = res.json()
    print(f"    [PASS] Quality records: {quality_records}")

    # 7. Perform match analysis on the same face photo
    print("\n[7] Simulating match analysis using the same face photo...")
    match_file = {"file": open(TEST_FACE_PATH, "rb")}
    res = requests.post(f"{BASE_URL}/cctv/match", files=match_file)
    assert res.status_code == 200, f"Face match query failed: {res.text}"
    match_res = res.json()
    
    assert match_res["total_faces_detected"] == 1, f"Expected 1 face, found: {match_res['total_faces_detected']}"
    match_details = match_res["results"][0]
    
    print(f"    [PASS] Total faces detected: {match_res['total_faces_detected']}")
    print(f"    [PASS] Liveness: {'LIVE' if match_details['is_live'] else 'SPOOF'} (Liveness Score: {match_details['liveness_score']}%)")
    print(f"    [PASS] Match Found: {match_details['match_found']}")
    print(f"    [PASS] Match Confidence: {match_details['match_confidence']}")
    print(f"    [PASS] Cosine Distance: {match_details['distance']}")
    print(f"    [PASS] Matched Suspect Label: {match_details['suspect_label']}")
    print(f"    [PASS] Model Used: {match_details['model_used']}")

    assert match_details["match_found"] is True, "Match was not found when uploading the identical image"
    assert match_details["suspect_id"] == suspect_id, "Match suspect ID did not match the registered suspect ID"
    assert match_details["match_confidence"] in ("CONFIRMED", "PROBABLE"), f"Unexpected confidence category: {match_details['match_confidence']}"

    # 8. Sighting verification
    # Find sighting in recent sightings
    print("\n[8] Verifying sighting record creation...")
    res = requests.get(f"{BASE_URL}/cctv/sightings/recent")
    assert res.status_code == 200, f"Recent sightings query failed: {res.text}"
    sightings = res.json()
    
    matching_sightings = [s for s in sightings if s["suspect_id"] == suspect_id]
    assert len(matching_sightings) > 0, "No sighting record logged in the database"
    sighting_id = matching_sightings[0]["id"]
    print(f"    [PASS] Found logged sighting entry: {matching_sightings[0]}")

    # Mark as verified
    print("\n[9] Testing officer manual verify endpoint...")
    res = requests.post(f"{BASE_URL}/cctv/sightings/{sighting_id}/verify", json={"verified": True, "officer_note": "Visual confirmation matches suspect records."})
    assert res.status_code == 200, f"Sighting verification failed: {res.text}"
    print(f"    [PASS] Sighting verified: {res.json()}")

    # 10. Clean up face entry
    print("\n[10] Testing face deletion cleanup...")
    res = requests.delete(f"{BASE_URL}/cctv/face/{suspect_id}/{face_id}")
    assert res.status_code == 200, f"Face deletion failed: {res.text}"
    print(f"    [PASS] Face deleted successfully.")

    print("\n" + "="*50)
    print("ALL CCTV SURVEILLANCE PIPELINE TESTS PASSED!")
    print("="*50 + "\n")

if __name__ == "__main__":
    test_cctv_pipeline()
