# api/data.py
import os
import time
from typing import Optional, Dict, List, Any
from passlib.hash import bcrypt

# Global in-memory stores (fallback)
_users = []
_records = []
_pool = None

async def get_pool():
    """
    Return None to force in-memory mode.
    This bypasses database connection issues.
    """
    return None

# ---------- User helpers (with fallback) ----------
async def find_user_by_api_key(api_key: str) -> Optional[Dict]:
    for user in _users:
        if user["apiKey"] == api_key:
            return user
    return None

async def find_user_by_username(username: str) -> Optional[Dict]:
    for user in _users:
        if user["username"] == username:
            return user
    return None

async def find_user_by_id(user_id: int) -> Optional[Dict]:
    for user in _users:
        if user["id"] == user_id:
            return user
    return None

async def create_user(username: str, password_hash: str, api_key: str, balance: float = 0.0) -> Dict:
    user = {
        "id": len(_users) + 1,
        "username": username,
        "passwordHash": password_hash,
        "apiKey": api_key,
        "balance": balance,
        "isActive": True
    }
    _users.append(user)
    return user

async def update_user_balance(user_id: int, amount: float) -> Optional[Dict]:
    for user in _users:
        if user["id"] == user_id:
            user["balance"] = max(0.0, user["balance"] + amount)
            return {
                "id": user["id"],
                "username": user["username"],
                "balance": user["balance"]
            }
    return None

# ---------- Record helpers (with fallback) ----------
async def create_record(
    user_id: int,
    identifier: str,
    field_a: str,
    field_b: str,
    field_c: str,
    school: str = "",
    requested_amount: float = 0.0
) -> Dict:
    record = {
        "id": len(_records) + 1,
        "userid": user_id,
        "identifier": identifier,
        "field_a": field_a,
        "field_b": field_b,
        "field_c": field_c,
        "school": school,
        "requested_amount": requested_amount,
        "status": "pending",
        "transaction_id": None,
        "message": None,
        "amount_paid": None,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime())
    }
    _records.append(record)
    return record

async def update_record_status(record_id: int, user_id: int, data: Dict) -> Optional[Dict]:
    for rec in _records:
        if rec["id"] == record_id and rec["userid"] == user_id:
            for key in ("status", "transaction_id", "message", "requested_amount", "amount_paid", "school"):
                if key in data:
                    rec[key] = data[key]
            return rec
    return None

async def get_next_record_for_user(user_id: int, requested_amount: Optional[float] = None) -> Optional[Dict]:
    # 1. Successful with amount
    if requested_amount is not None:
        for rec in sorted(_records, key=lambda x: x.get("created_at", ""), reverse=True):
            if rec["userid"] == user_id and rec["status"] == "success" and rec["requested_amount"] == requested_amount:
                return rec
    # 2. Pending
    for rec in _records:
        if rec["userid"] == user_id and rec["status"] == "pending":
            return rec
    # 3. Any successful
    for rec in sorted(_records, key=lambda x: x.get("created_at", ""), reverse=True):
        if rec["userid"] == user_id and rec["status"] == "success":
            return rec
    return None

# ---------- Admin helpers ----------
async def get_all_users() -> List[Dict]:
    return [{"id": u["id"], "username": u["username"], "balance": u["balance"], "apikey": u["apiKey"], "isactive": u["isActive"]} for u in _users]

async def get_all_records() -> List[Dict]:
    return _records.copy()

# ---------- Delete helpers ----------
async def delete_record(record_id: int) -> bool:
    for idx, rec in enumerate(_records):
        if rec["id"] == record_id:
            del _records[idx]
            return True
    return False

async def clear_all_records() -> int:
    count = len(_records)
    _records.clear()
    return count

# ---------- Database initialization (no-op) ----------
async def init_db():
    # No-op: we use in-memory store
    pass

# ---------- Seed demo data ----------
async def seed_demo_data():
    if _users:
        return  # Already seeded

    # Create demo user
    hashed = bcrypt.hash("password123")
    user = await create_user("demo", hashed, "demo-api-key-123", 100.0)

    # Insert 10 sample records
    for i in range(1, 11):
        await create_record(
            user_id=user["id"],
            identifier=f"411111111111111{i:02d}",
            field_a=f"{i % 12 + 1:02d}",
            field_b="26",
            field_c=str(100 + i % 900),
            school=f"Demo School {i}",
            requested_amount=1.0 + (i % 5) * 0.5
        )
