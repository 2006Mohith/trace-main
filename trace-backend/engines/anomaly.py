"""
Engine 4: Anomaly Detection using Isolation Forest
Computes behavioral features per suspect and flags outliers.
"""
from typing import List
from collections import Counter
import uuid
import numpy as np
from sqlalchemy.orm import Session
from models import CDRRecord, Suspect, Event

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def _compute_features(suspect: Suspect, cdrs: list) -> dict:
    if not cdrs:
        return {}

    calls = [r for r in cdrs if r.call_type == "CALL"]
    sms = [r for r in cdrs if r.call_type == "SMS"]
    total = len(cdrs)

    # Unique contacts
    unique_contacts = len(set(r.msisdn_b for r in cdrs))

    # Calls per day
    from collections import defaultdict
    day_counts: dict = defaultdict(int)
    for r in cdrs:
        day_counts[r.timestamp.date()] += 1
    daily_vals = list(day_counts.values())
    calls_per_day_mean = float(np.mean(daily_vals)) if daily_vals else 0
    calls_per_day_std = float(np.std(daily_vals)) if daily_vals else 0

    # Night call ratio (23:00 - 05:00)
    night_calls = [r for r in calls if r.timestamp.hour >= 23 or r.timestamp.hour < 5]
    night_call_ratio = len(night_calls) / len(calls) if calls else 0

    # Burst score: max calls in any 6-hour window / avg per 6-hour window
    bins: Counter = Counter()
    for r in cdrs:
        bucket = (r.timestamp.date(), r.timestamp.hour // 6)
        bins[bucket] += 1
    max_bin = max(bins.values()) if bins else 0
    avg_bin = sum(bins.values()) / len(bins) if bins else 0
    burst_score = max_bin / avg_bin if avg_bin > 0 else 0

    # Avg call duration
    durations = [r.duration_sec for r in calls if r.duration_sec and r.duration_sec > 0]
    avg_call_duration = float(np.mean(durations)) if durations else 0

    # SMS ratio
    sms_ratio = len(sms) / total if total else 0

    # Silence after burst: > 50% drop in calls the day after the burst day
    if bins:
        peak_bucket = max(bins, key=bins.get)
        from datetime import timedelta
        peak_date = peak_bucket[0]
        next_date = peak_date + timedelta(days=1)
        peak_count = bins[peak_bucket]
        next_counts = sum(v for (d, _), v in bins.items() if d == next_date)
        silence_after_burst = 1.0 if (peak_count > 0 and next_counts < peak_count * 0.5) else 0.0
    else:
        silence_after_burst = 0.0

    return {
        "calls_per_day_mean": calls_per_day_mean,
        "calls_per_day_std": calls_per_day_std,
        "unique_contacts_count": float(unique_contacts),
        "night_call_ratio": night_call_ratio,
        "burst_score": burst_score,
        "avg_call_duration_sec": avg_call_duration,
        "sms_ratio": sms_ratio,
        "silence_after_burst": silence_after_burst,
    }


def detect_anomalies(case_id: str, db: Session) -> List[Event]:
    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()
    if not suspects:
        return []

    feature_vectors = []
    suspect_features = []

    for suspect in suspects:
        cdrs = db.query(CDRRecord).filter(CDRRecord.suspect_id == suspect.id).all()
        feats = _compute_features(suspect, cdrs)
        if not feats:
            feats = {k: 0.0 for k in [
                "calls_per_day_mean", "calls_per_day_std", "unique_contacts_count",
                "night_call_ratio", "burst_score", "avg_call_duration_sec",
                "sms_ratio", "silence_after_burst",
            ]}
        suspect_features.append((suspect, feats))
        feature_vectors.append([
            feats["calls_per_day_mean"],
            feats["calls_per_day_std"],
            feats["unique_contacts_count"],
            feats["night_call_ratio"],
            feats["burst_score"],
            feats["avg_call_duration_sec"],
            feats["sms_ratio"],
            feats["silence_after_burst"],
        ])

    if not SKLEARN_AVAILABLE or len(feature_vectors) < 2:
        return []

    X = np.array(feature_vectors)
    clf = IsolationForest(contamination=0.2, random_state=42)
    clf.fit(X)
    scores = clf.score_samples(X)  # negative; more negative = more anomalous
    predictions = clf.predict(X)   # -1 = outlier

    events: List[Event] = []
    for i, (suspect, feats) in enumerate(suspect_features):
        score = float(scores[i])
        if score < -0.1 and predictions[i] == -1:
            triggered = []
            if feats["night_call_ratio"] > 0.25:
                triggered.append("high_night_call_ratio")
            if feats["burst_score"] > 3:
                triggered.append("call_burst_detected")
            if feats["silence_after_burst"] > 0:
                triggered.append("silence_after_burst")
            if feats["unique_contacts_count"] > 10:
                triggered.append("many_unique_contacts")

            events.append(Event(
                id=str(uuid.uuid4()),
                case_id=case_id,
                event_type="ANOMALY",
                severity="HIGH",
                involved_suspects=[suspect.label],
                detail={
                    "anomaly_score": round(score, 4),
                    "features_summary": {k: round(v, 3) for k, v in feats.items()},
                    "triggered_features": triggered,
                    "note": "Confidence increases with more suspect data. Based on IsolationForest(contamination=0.2).",
                },
                occurred_at=None,
            ))

    return events
