# api/records.py
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from typing import Optional, List
from .data import (
    find_user_by_api_key,
    find_user_by_id,
    find_user_by_username,
    get_next_record_for_user,
    update_record_status,
    update_user_balance,
    create_record,
    get_all_records,
    get_all_users,
    records
)

router = APIRouter(prefix="/api/extension/records", tags=["records"])

# Helper to extract user from Authorization header
def get_user_from_request(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    api_key = auth[7:]
    user = find_user_by_api_key(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user

class NextRecordResponse(BaseModel):
    id: int
    identifier: str
    field_a: str
    field_b: str
    field_c: str
    school: str
    requested_amount: float
    balance: str
    payment_result_wait_seconds: int = 5

@router.get("/next", response_model=NextRecordResponse)
async def get_next_record(request: Request, requested_amount: Optional[float] = None):
    user = get_user_from_request(request)
    # First attempt with the given amount
    record = get_next_record_for_user(user["id"], requested_amount)
    if not record and requested_amount is not None:
        # Fallback: try without amount filter
        record = get_next_record_for_user(user["id"], None)
    if not record:
        raise HTTPException(status_code=404, detail="No available records")
    return NextRecordResponse(
        id=record["id"],
        identifier=record["identifier"],
        field_a=record["field_a"],
        field_b=record["field_b"],
        field_c=record["field_c"],
        school=record.get("school", ""),
        requested_amount=record["requested_amount"],
        balance=f"{user['balance']:.2f}"
    )

class StatusUpdateRequest(BaseModel):
    status: str
    transaction_id: Optional[str] = None
    message: Optional[str] = None
    requested_amount: Optional[float] = None
    amount_paid: Optional[float] = None
    school: Optional[str] = None

class StatusUpdateResponse(BaseModel):
    balance: str
    record_status: str
    message: Optional[str] = None

@router.put("/{record_id}/status", response_model=StatusUpdateResponse)
async def update_status(request: Request, record_id: int, data: StatusUpdateRequest):
    user = get_user_from_request(request)
    if data.status not in ("success", "failed"):
        raise HTTPException(status_code=400, detail='Status must be "success" or "failed"')

    updated = update_record_status(
        record_id,
        user["id"],
        data.dict(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or not owned by user")

    if data.status == "success" and data.amount_paid and data.amount_paid > 0:
        update_user_balance(user["id"], -data.amount_paid)
        # refresh user balance from store
        user = find_user_by_id(user["id"])

    return StatusUpdateResponse(
        balance=f"{user['balance']:.2f}",
        record_status=updated["status"],
        message=updated.get("message")
    )

# ---------- Admin endpoints ----------
class CreateRecordRequest(BaseModel):
    user_id: Optional[int] = None
    identifier: str
    field_a: str
    field_b: str
    field_c: str
    school: str = ""
    requested_amount: float = 0.0

@router.post("/admin/records")
async def admin_create_record(data: CreateRecordRequest):
    # if user_id not provided, use user 1 (or create a default)
    user_id = data.user_id
    if user_id is None:
        user = find_user_by_id(1)
        if not user:
            # create a default user
            from passlib.hash import bcrypt
            hashed = bcrypt.hash("password123")
            user = create_user("default", hashed, "default-api-key", 0.0)
            user_id = user["id"]
        else:
            user_id = 1
    # Check for duplicate (same identifier, expiry, cvv)
    existing = next((r for r in records if r["identifier"] == data.identifier and r["field_a"] == data.field_a and r["field_b"] == data.field_b and r["field_c"] == data.field_c), None)
    if existing:
        raise HTTPException(status_code=409, detail="Record already exists")
    rec = create_record(user_id, data.identifier, data.field_a, data.field_b, data.field_c, data.school, data.requested_amount)
    return rec

class TopUpRequest(BaseModel):
    username: str
    amount: float

@router.post("/admin/topup")
async def admin_topup(data: TopUpRequest):
    user = find_user_by_username(data.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated = update_user_balance(user["id"], data.amount)
    return {"username": data.username, "new_balance": f"{updated['balance']:.2f}"}

@router.get("/admin/users")
async def admin_list_users():
    return get_all_users()

@router.get("/admin/records")
async def admin_list_records():
    return get_all_records()

# CSV Import
class CSVImportRequest(BaseModel):
    csv_data: str  # multiline string with records

@router.post("/admin/import-csv")
async def admin_import_csv(data: CSVImportRequest):
    lines = data.csv_data.strip().split('\n')
    created = []
    errors = []
    for idx, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        # Format: card_number|month|year|cvv|school|amount (school and amount optional)
        parts = line.split('|')
        if len(parts) < 4:
            errors.append(f"Line {idx}: insufficient fields (need card|month|year|cvv)")
            continue
        identifier = parts[0].strip()
        field_a = parts[1].strip()
        field_b = parts[2].strip()
        field_c = parts[3].strip()
        school = parts[4].strip() if len(parts) > 4 else ""
        requested_amount = float(parts[5].strip()) if len(parts) > 5 and parts[5].strip() else 0.0
        # Check duplicate
        existing = next((r for r in records if r["identifier"] == identifier and r["field_a"] == field_a and r["field_b"] == field_b and r["field_c"] == field_c), None)
        if existing:
            errors.append(f"Line {idx}: duplicate record (card {identifier})")
            continue
        # Use default user 1 (or you can add a user_id column)
        user_id = 1
        rec = create_record(user_id, identifier, field_a, field_b, field_c, school, requested_amount)
        created.append(rec)
    return {"created": created, "errors": errors}

# ---------- DELETE endpoints ----------
@router.delete("/admin/records/{record_id}")
async def admin_delete_record(record_id: int):
    global records
    # Find and remove the record
    for idx, r in enumerate(records):
        if r["id"] == record_id:
            deleted = records.pop(idx)
            return {"deleted": deleted}
    raise HTTPException(status_code=404, detail="Record not found")

@router.delete("/admin/records")
async def admin_clear_records():
    global records
    count = len(records)
    records.clear()
    return {"deleted_count": count}
