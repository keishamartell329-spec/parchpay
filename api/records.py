# api/records.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
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
    delete_record,
    clear_all_records,
)

router = APIRouter(prefix="/api/extension/records", tags=["records"])

async def get_user_from_request(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    api_key = auth[7:]
    user = await find_user_by_api_key(api_key)   # FIX: await
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
    user = await get_user_from_request(request)
    record = await get_next_record_for_user(user["id"], requested_amount)
    if not record and requested_amount is not None:
        record = await get_next_record_for_user(user["id"], None)
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
    user = await get_user_from_request(request)
    if data.status not in ("success", "failed"):
        raise HTTPException(status_code=400, detail='Status must be "success" or "failed"')
    updated = await update_record_status(record_id, user["id"], data.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or not owned by user")
    if data.status == "success" and data.amount_paid and data.amount_paid > 0:
        await update_user_balance(user["id"], -data.amount_paid)
        user = await find_user_by_id(user["id"])
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
    user_id = data.user_id
    if user_id is None:
        user = await find_user_by_id(1)
        if not user:
            from passlib.hash import bcrypt
            hashed = bcrypt.hash("password123")
            user = await create_user("default", hashed, "default-api-key", 0.0)
            user_id = user["id"]
        else:
            user_id = 1
    # duplicate check using data layer
    all_recs = await get_all_records()
    for rec in all_recs:
        if (rec["identifier"] == data.identifier and
            rec["field_a"] == data.field_a and
            rec["field_b"] == data.field_b and
            rec["field_c"] == data.field_c):
            raise HTTPException(status_code=409, detail="Record already exists")
    rec = await create_record(user_id, data.identifier, data.field_a, data.field_b, data.field_c, data.school, data.requested_amount)
    return rec

class TopUpRequest(BaseModel):
    username: str
    amount: float

@router.post("/admin/topup")
async def admin_topup(data: TopUpRequest):
    user = await find_user_by_username(data.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated = await update_user_balance(user["id"], data.amount)
    return {"username": data.username, "new_balance": f"{updated['balance']:.2f}"}

@router.get("/admin/users")
async def admin_list_users():
    return await get_all_users()

@router.get("/admin/records")
async def admin_list_records():
    return await get_all_records()

class CSVImportRequest(BaseModel):
    csv_data: str

@router.post("/admin/import-csv")
async def admin_import_csv(data: CSVImportRequest):
    lines = data.csv_data.strip().split('\n')
    created = []
    errors = []
    existing = await get_all_records()
    for idx, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        parts = line.split('|')
        if len(parts) < 4:
            errors.append(f"Line {idx}: insufficient fields")
            continue
        identifier, field_a, field_b, field_c = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        school = parts[4].strip() if len(parts) > 4 else ""
        requested_amount = float(parts[5].strip()) if len(parts) > 5 and parts[5].strip() else 0.0
        # duplicate check
        dup = any(r["identifier"] == identifier and r["field_a"] == field_a and r["field_b"] == field_b and r["field_c"] == field_c for r in existing)
        if dup:
            errors.append(f"Line {idx}: duplicate")
            continue
        rec = await create_record(1, identifier, field_a, field_b, field_c, school, requested_amount)
        created.append(rec)
        existing.append(rec)
    return {"created": created, "errors": errors}

@router.delete("/admin/records/{record_id}")
async def admin_delete_record(record_id: int):
    deleted = await delete_record(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"deleted": True, "id": record_id}

@router.delete("/admin/records")
async def admin_clear_records():
    count = await clear_all_records()
    return {"deleted_count": count}
