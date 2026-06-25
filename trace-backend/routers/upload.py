import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import pandas as pd
from database import get_db
from models import Case, Suspect, CDRRecord, IPDRRecord
from schemas import UploadResponse

router = APIRouter(tags=["upload"])

CDR_COLUMNS = {"msisdn_a", "msisdn_b", "imei", "tower_id", "tower_lat",
               "tower_lon", "call_type", "duration_sec", "timestamp"}
IPDR_COLUMNS = {"msisdn", "dest_ip", "dest_port", "data_volume_kb", "timestamp"}


def _parse_cdr_csv(content: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(content))
    
    # Try mapping from Operator layout first if required fields aren't present
    if "msisdn_a" not in df.columns:
        mapping = {
            "A_Party_MSISDN": "msisdn_a",
            "B_Party_MSISDN": "msisdn_b",
            "IMEI": "imei",
            "Cell_ID": "tower_id",
            "Tower_Latitude": "tower_lat",
            "Tower_Longitude": "tower_lon",
            "Call_Type": "call_type",
            "Duration_Sec": "duration_sec"
        }
        rename_dict = {k: v for k, v in mapping.items() if k in df.columns}
        df = df.rename(columns=rename_dict)
        
        # Build timestamp if Date & Time are present
        if "Date" in df.columns and "Time" in df.columns:
            df["timestamp"] = df["Date"].astype(str) + " " + df["Time"].astype(str)

    missing = CDR_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CDR CSV missing columns: {missing}")

    def parse_datetime(val):
        val_str = str(val).strip()
        for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S"):
            try:
                return pd.to_datetime(val_str, format=fmt)
            except:
                continue
        return pd.to_datetime(val_str, errors="coerce")

    df["timestamp"] = df["timestamp"].apply(parse_datetime)
    df["timestamp"] = df["timestamp"].fillna(datetime.utcnow())
    df["duration_sec"] = pd.to_numeric(df["duration_sec"], errors="coerce").fillna(0).astype(int)
    df["tower_lat"] = pd.to_numeric(df["tower_lat"], errors="coerce")
    df["tower_lon"] = pd.to_numeric(df["tower_lon"], errors="coerce")
    return df


def _parse_ipdr_csv(content: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(content))

    if "msisdn" not in df.columns:
        mapping = {
            "MSISDN": "msisdn",
            "Dest_IP": "dest_ip",
            "Dest_Port": "dest_port",
        }
        rename_dict = {k: v for k, v in mapping.items() if k in df.columns}
        df = df.rename(columns=rename_dict)

        # Calculate data_volume_kb
        if "Download_KB" in df.columns or "Upload_KB" in df.columns:
            down = pd.to_numeric(df.get("Download_KB", 0), errors="coerce").fillna(0)
            up = pd.to_numeric(df.get("Upload_KB", 0), errors="coerce").fillna(0)
            df["data_volume_kb"] = down + up

        # Build timestamp
        if "Start_Date" in df.columns and "Start_Time" in df.columns:
            df["timestamp"] = df["Start_Date"].astype(str) + " " + df["Start_Time"].astype(str)

    # Include app_label if present
    if "App_Label" in df.columns:
        df["app_label"] = df["App_Label"]
    elif "app_label" not in df.columns:
        df["app_label"] = "Unknown"

    missing = IPDR_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"IPDR CSV missing columns: {missing}")

    def parse_datetime(val):
        val_str = str(val).strip()
        for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S"):
            try:
                return pd.to_datetime(val_str, format=fmt)
            except:
                continue
        return pd.to_datetime(val_str, errors="coerce")

    df["timestamp"] = df["timestamp"].apply(parse_datetime)
    df["timestamp"] = df["timestamp"].fillna(datetime.utcnow())
    df["data_volume_kb"] = pd.to_numeric(df["data_volume_kb"], errors="coerce").fillna(0)
    df["dest_port"] = pd.to_numeric(df["dest_port"], errors="coerce").fillna(0).astype(int)
    return df


@router.post("/cases/{case_id}/upload", response_model=UploadResponse, status_code=201)
async def upload_records(
    case_id: str,
    suspect_label: str = Form(...),
    cdr_file: UploadFile = File(...),
    ipdr_file: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Parse CDR
    cdr_content = await cdr_file.read()
    try:
        cdr_df = _parse_cdr_csv(cdr_content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Determine primary MSISDN from CDR — ensure it's a native Python str
    primary_msisdn = str(cdr_df["msisdn_a"].mode().iloc[0]) if not cdr_df.empty else "UNKNOWN"

    # Create suspect
    suspect = Suspect(case_id=case_id, label=suspect_label, primary_msisdn=primary_msisdn)
    db.add(suspect)
    db.flush()

    # Insert CDR records
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

    # Parse and insert IPDR
    ipdr_count = 0
    if ipdr_file:
        ipdr_content = await ipdr_file.read()
        if ipdr_content:
            try:
                ipdr_df = _parse_ipdr_csv(ipdr_content)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
            ipdr_rows = []
            for _, row in ipdr_df.iterrows():
                ipdr_rows.append(IPDRRecord(
                    suspect_id=suspect.id,
                    msisdn=str(row["msisdn"]),
                    dest_ip=str(row["dest_ip"]),
                    dest_port=int(row["dest_port"]),
                    data_volume_kb=float(row["data_volume_kb"]),
                    app_label=str(row["app_label"]) if "app_label" in row and pd.notna(row["app_label"]) else "Unknown",
                    timestamp=row["timestamp"].to_pydatetime(),
                ))
            db.add_all(ipdr_rows)
            ipdr_count = len(ipdr_rows)

    db.commit()
    db.refresh(suspect)

    return UploadResponse(
        suspect_id=suspect.id,
        rows_inserted_cdr=len(cdr_rows),
        rows_inserted_ipdr=ipdr_count,
    )


# ── Template downloads ─────────────────────────────────────────────────────────

@router.get("/templates/cdr")
def download_cdr_template():
    content = "msisdn_a,msisdn_b,imei,tower_id,tower_lat,tower_lon,call_type,duration_sec,timestamp\n"
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cdr_template.csv"},
    )


@router.get("/templates/ipdr")
def download_ipdr_template():
    content = "msisdn,dest_ip,dest_port,data_volume_kb,timestamp\n"
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ipdr_template.csv"},
    )
