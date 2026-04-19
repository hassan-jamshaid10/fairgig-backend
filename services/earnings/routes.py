import os
import io
import pandas as pd
import cloudinary
import cloudinary.uploader
from datetime import date, timedelta, datetime
from typing import Annotated, Optional, List
from pathlib import Path
from uuid import UUID
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from jose import JWTError

from shared.database import get_db
from shared.security import decode_access_token
from services.earnings.models import ShiftORM
from shared.schemas import (
    ShiftCreate, 
    ShiftRead, 
    ShiftReadWithStatus, 
    ShiftHistoryResponse,
    ScreenshotRead,
    PendingQueueResponse,
    ScreenshotVerifyRequest,
    WorkerScreenshotsResponse
)

# 1. LOAD ENVIRONMENT
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env.local"
load_dotenv(dotenv_path=env_path)

# 2. CLOUDINARY CONFIGURATION
raw_url = os.getenv("CLOUDINARY_URL", "").strip('"').strip("'")
if raw_url.startswith("cloudinary://"):
    try:
        content = raw_url.replace("cloudinary://", "")
        auth_part, cloud_name = content.split("@")
        api_key, api_secret = auth_part.split(":")
        cloudinary.config(
            cloud_name=cloud_name, 
            api_key=api_key, 
            api_secret=api_secret, 
            secure=True
        )
    except Exception:
        pass

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/auth/login")

# AUTH DEPENDENCIES

async def get_token_payload(
    access_token: Optional[str] = Query(None),
    header_token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="http://localhost:8001/auth/login", auto_error=False))
) -> dict:
    token = access_token or header_token
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    try:
        payload = decode_access_token(token)
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token.")

async def get_current_worker(payload: dict = Depends(get_token_payload)) -> str:
    if payload.get("role", "").lower() != "worker":
        raise HTTPException(status_code=403, detail="Workers only.")
    return payload.get("sub")

async def get_verifier_or_advocate(payload: dict = Depends(get_token_payload)) -> dict:
    if payload.get("role", "").lower() not in ["verifier", "advocate"]:
        raise HTTPException(status_code=403, detail="Admins only.")
    return payload

async def get_current_verifier(payload: dict = Depends(get_token_payload)) -> dict:
    if payload.get("role", "").lower() != "verifier":
        raise HTTPException(status_code=403, detail="Only Verifiers allowed.")
    return payload

# ENDPOINTS

# Endpoint 1: Log Shift
@router.post("/shifts", response_model=ShiftRead, status_code=201)
async def create_shift(payload: ShiftCreate, worker_id: Annotated[str, Depends(get_current_worker)], db: AsyncSession = Depends(get_db)):
    if payload.shift_date > date.today():
        raise HTTPException(status_code=400, detail="Future dates not allowed.")
    new_shift = ShiftORM(worker_id=worker_id, **payload.model_dump())
    db.add(new_shift)
    await db.commit()
    await db.refresh(new_shift)
    return new_shift

# Endpoint 2: Import CSV (Fully Detailed Logic)
@router.post("/shifts/import-csv")
async def import_shifts_csv(file: UploadFile = File(...), worker_id: str = Depends(get_current_worker), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSV only.")
    
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))
    
    required = ["platform", "shift_date", "hours_worked", "gross_earned", "platform_deductions"]
    if not all(col in df.columns for col in required):
        raise HTTPException(status_code=400, detail="Missing required columns.")

    import_errors = []
    valid_shifts = []

    for index, row in df.iterrows():
        line = index + 2
        try:
            s_date = pd.to_datetime(row['shift_date']).date()
            if s_date > date.today():
                raise ValueError("Future date")
            
            hours = float(row['hours_worked'])
            gross = float(row['gross_earned'])
            deduct = float(row['platform_deductions'])
            
            if hours <= 0:
                raise ValueError("Invalid hours")
            
            net = row.get('net_received')
            if pd.isna(net):
                net = gross - deduct
            
            valid_shifts.append(ShiftORM(
                worker_id=worker_id, platform=str(row['platform']), shift_date=s_date,
                hours_worked=hours, gross_earned=gross, platform_deductions=deduct,
                net_received=float(net), notes=str(row.get('notes')) if not pd.isna(row.get('notes')) else None
            ))
        except Exception as e:
            import_errors.append({"row": line, "reason": str(e)})

    if valid_shifts:
        db.add_all(valid_shifts)
        await db.commit()
    
    return {"imported_count": len(valid_shifts), "errors": import_errors}

# Endpoint 3: Worker History
@router.get("/shifts/me", response_model=ShiftHistoryResponse)
async def get_my_shifts(db: AsyncSession = Depends(get_db), worker_id: str = Depends(get_current_worker), start_date: date = Query(default=date.today() - timedelta(days=60), alias="from"), end_date: date = Query(default=date.today(), alias="to"), platform: Optional[str] = None, limit: int = 100, offset: int = 0):
    query = "SELECT s.*, COALESCE(sc.status, 'None') as screenshot_status, sc.image_url as screenshot_url FROM earnings_svc.shifts s LEFT JOIN earnings_svc.screenshots sc ON sc.shift_id = s.id WHERE s.worker_id = :worker_id AND s.shift_date BETWEEN :start AND :end"
    if platform: query += " AND s.platform = :plat"
    query += " ORDER BY s.shift_date DESC LIMIT :limit OFFSET :offset"
    res = await db.execute(text(query), {"worker_id": worker_id, "start": start_date, "end": end_date, "limit": limit, "offset": offset, "plat": platform})
    data = [dict(row) for row in res.mappings().all()]
    total = await db.scalar(text("SELECT COUNT(*) FROM earnings_svc.shifts WHERE worker_id = :worker_id"), {"worker_id": worker_id})
    return {"shifts": data, "total": total or 0}

# Endpoint 4: Admin History
@router.get("/shifts", response_model=ShiftHistoryResponse)
async def admin_get_shifts(worker_id: UUID, admin_payload: dict = Depends(get_verifier_or_advocate), db: AsyncSession = Depends(get_db)):
    query = "SELECT s.*, COALESCE(sc.status, 'None') as screenshot_status, sc.image_url as screenshot_url FROM earnings_svc.shifts s LEFT JOIN earnings_svc.screenshots sc ON sc.shift_id = s.id WHERE s.worker_id = :worker_id ORDER BY s.shift_date DESC"
    res = await db.execute(text(query), {"worker_id": str(worker_id)})
    data = [dict(row) for row in res.mappings().all()]
    return {"shifts": data, "total": len(data)}

# Endpoint 5: Upload Screenshot
@router.post("/screenshots", response_model=ScreenshotRead, status_code=201)
async def upload_screenshot(shift_id: UUID = Form(...), file: UploadFile = File(...), worker_id: str = Depends(get_current_worker), db: AsyncSession = Depends(get_db)):
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Images only.")
    
    res = await db.execute(text("SELECT worker_id FROM earnings_svc.shifts WHERE id = :sid"), {"sid": str(shift_id)})
    if res.scalar() != worker_id:
        raise HTTPException(status_code=403, detail="Denied.")
    
    up = cloudinary.uploader.upload(file.file, folder=f"fairgig/screenshots/{worker_id}", public_id=f"shift_{shift_id}", overwrite=True)
    url = up.get("secure_url")
    
    await db.execute(text("INSERT INTO earnings_svc.screenshots (shift_id, image_url, status) VALUES (:sid, :url, 'Pending') ON CONFLICT (shift_id) DO UPDATE SET image_url = :url, status = 'Pending'"), {"sid": str(shift_id), "url": url})
    await db.commit()
    
    final = await db.execute(text("SELECT * FROM earnings_svc.screenshots WHERE shift_id = :sid"), {"sid": str(shift_id)})
    return final.mappings().first()

# Endpoint 6: Pending Queue
@router.get("/screenshots/pending", response_model=PendingQueueResponse)
async def get_pending_screenshots(limit: int = 50, offset: int = 0, verifier: dict = Depends(get_current_verifier), db: AsyncSession = Depends(get_db)):
    query = """
        SELECT sc.*, s.id as s_id, s.worker_id as s_worker_id, s.platform as s_platform, s.shift_date as s_shift_date, 
               s.hours_worked as s_hours_worked, s.gross_earned as s_gross_earned, s.platform_deductions as s_platform_deductions, 
               s.net_received as s_net_received, s.notes as s_notes, s.created_at as s_created_at
        FROM earnings_svc.screenshots sc JOIN earnings_svc.shifts s ON sc.shift_id = s.id
        WHERE sc.status = 'Pending' ORDER BY sc.created_at ASC LIMIT :limit OFFSET :offset
    """
    res = await db.execute(text(query), {"limit": limit, "offset": offset})
    rows = res.mappings().all()
    formatted = []
    for r in rows:
        shift_obj = {"id": r["s_id"], "worker_id": r["s_worker_id"], "platform": r["s_platform"], "shift_date": r["s_shift_date"], "hours_worked": r["s_hours_worked"], "gross_earned": r["s_gross_earned"], "platform_deductions": r["s_platform_deductions"], "net_received": r["s_net_received"], "notes": r["s_notes"], "created_at": r["s_created_at"]}
        formatted.append({"shift_id": r["shift_id"], "image_url": r["image_url"], "status": r["status"], "created_at": r["created_at"], "shift": shift_obj})
    total = await db.scalar(text("SELECT COUNT(*) FROM earnings_svc.screenshots WHERE status = 'Pending'"))
    return {"screenshots": formatted, "total": total or 0}

# Endpoint 7: Verify Action
@router.patch("/screenshots/{shift_id}/verify", response_model=ScreenshotRead)
async def verify_screenshot(shift_id: UUID, payload: ScreenshotVerifyRequest, v_payload: dict = Depends(get_current_verifier), db: AsyncSession = Depends(get_db)):
    res = await db.execute(text("SELECT status FROM earnings_svc.screenshots WHERE shift_id = :sid"), {"sid": str(shift_id)})
    cur_status = res.scalar()
    if not cur_status: raise HTTPException(status_code=404, detail="Not found.")
    if cur_status != "Pending": raise HTTPException(status_code=400, detail=f"Already {cur_status}.")
    if payload.status in ["Flagged", "Unverifiable"] and not payload.note:
        raise HTTPException(status_code=400, detail="Note required for rejection.")

    await db.execute(text("""
        UPDATE earnings_svc.screenshots SET status = :status, verifier_id = :v_id, verification_note = :note, verified_at = NOW() WHERE shift_id = :sid
    """), {"status": payload.status, "v_id": v_payload.get("sub"), "note": payload.note, "sid": str(shift_id)})
    await db.commit()
    final = await db.execute(text("SELECT * FROM earnings_svc.screenshots WHERE shift_id = :sid"), {"sid": str(shift_id)})
    return final.mappings().first()
# Endpoint 8: Worker's Own Screenshot Status
@router.get("/screenshots/mine", response_model=WorkerScreenshotsResponse)
async def get_my_screenshots(
    limit: int = 50,
    offset: int = 0,
    worker_id: str = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db)
):
    """Allows a worker to see the verification status of their own screenshots."""
    
    # We join screenshots with shifts but filter by the worker'_id from the JWT
    query_str = """
        SELECT sc.*, 
               s.platform as s_platform, 
               s.shift_date as s_shift_date, 
               s.net_received as s_net_received
        FROM earnings_svc.screenshots sc
        JOIN earnings_svc.shifts s ON sc.shift_id = s.id
        WHERE s.worker_id = :worker_id
        ORDER BY sc.created_at DESC
        LIMIT :limit OFFSET :offset
    """
    
    result = await db.execute(text(query_str), {
        "worker_id": worker_id, 
        "limit": limit, 
        "offset": offset
    })
    rows = result.mappings().all()

    formatted = []
    for row in rows:
        # Create the nested shift object required by the schema
        shift_context = {
            "platform": row["s_platform"],
            "shift_date": row["s_shift_date"],
            "net_received": row["s_net_received"]
        }
        
        formatted.append({
            "shift_id": row["shift_id"],
            "image_url": row["image_url"],
            "status": row["status"],
            "verified_at": row["verified_at"],
            "created_at": row["created_at"],
            "shift": shift_context
        })

    # Get total count for pagination
    total = await db.scalar(
        text("""
            SELECT COUNT(*) 
            FROM earnings_svc.screenshots sc
            JOIN earnings_svc.shifts s ON sc.shift_id = s.id
            WHERE s.worker_id = :worker_id
        """), 
        {"worker_id": worker_id}
    )

    return {
        "screenshots": formatted,
        "total": total or 0
    }