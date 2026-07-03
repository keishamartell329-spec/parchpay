# api/records.py
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from typing import Optional
from .data import (
    find_user_by_api_key,
    get_next_record_for_user,
    update_record_status,
    update_user_balance,
    create_record,
    find_user_by_id,
    find_user_by_username,
    get_all_users,
    get_all_records
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
    record = get_next_record_for_user(user["id"], requested_amount)
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

# ---------- Admin endpoints (for testing) ----------

@router.post("/admin/records")
async def admin_create_record(
    user_id: int,
    identifier: str,
    field_a: str,
    field_b: str,
    field_c: str,
    school: str = "",
    requested_amount: float = 0.0
):
    if not find_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    rec = create_record(user_id, identifier, field_a, field_b, field_c, school, requested_amount)
    return rec

@router.post("/admin/topup")
async def admin_topup(username: str, amount: float):
    user = find_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated = update_user_balance(user["id"], amount)
    return {"username": username, "new_balance": f"{updated['balance']:.2f}"}

# ---------- Admin GET endpoints (for the admin panel) ----------

@router.get("/admin/users")
async def admin_list_users():
    """List all users (no auth for demo – add protection in production)"""
    return get_all_users()

@router.get("/admin/records")
async def admin_list_records():
    """List all records (no auth for demo)"""
    return get_all_records()
