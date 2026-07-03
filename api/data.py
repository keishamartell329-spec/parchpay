# api/data.py
from typing import Optional, List, Dict, Any
import time

# In-memory stores
users: List[Dict[str, Any]] = []
records: List[Dict[str, Any]] = []

# ---------- User helpers ----------
def find_user_by_api_key(api_key: str) -> Optional[Dict]:
    return next((u for u in users if u["apiKey"] == api_key), None)

def find_user_by_username(username: str) -> Optional[Dict]:
    return next((u for u in users if u["username"] == username), None)

def find_user_by_id(user_id: int) -> Optional[Dict]:
    return next((u for u in users if u["id"] == user_id), None)

def create_user(username: str, password_hash: str, api_key: str, balance: float = 0.0) -> Dict:
    user = {
        "id": len(users) + 1,
        "username": username,
        "passwordHash": password_hash,
        "apiKey": api_key,
        "balance": balance,
        "isActive": True,
    }
    users.append(user)
    return user

# ---------- Record helpers ----------
def get_next_record_for_user(user_id: int, requested_amount: Optional[float] = None) -> Optional[Dict]:
    candidates = [
        r for r in records
        if r["userId"] == user_id
        and r["status"] not in ("success", "failed")
    ]
    if requested_amount is not None:
        candidates = [r for r in candidates if r["requested_amount"] == requested_amount]
    if not candidates:
        # fallback: any pending record
        candidates = [r for r in records if r["userId"] == user_id and r["status"] not in ("success", "failed")]
    return candidates[0] if candidates else None

def create_record(
    user_id: int,
    identifier: str,
    field_a: str,
    field_b: str,
    field_c: str,
    school: str = "",
    requested_amount: float = 0.0
) -> Dict:
    record = {
        "id": len(records) + 1,
        "userId": user_id,
        "identifier": identifier,
        "field_a": field_a,
        "field_b": field_b,
        "field_c": field_c,
        "school": school,
        "requested_amount": float(requested_amount),
        "status": "pending",
        "transaction_id": None,
        "message": None,
        "amount_paid": None,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime())
    }
    records.append(record)
    return record

def update_record_status(record_id: int, user_id: int, data: Dict) -> Optional[Dict]:
    record = next((r for r in records if r["id"] == record_id and r["userId"] == user_id), None)
    if not record:
        return None
    record["status"] = data.get("status")
    record["transaction_id"] = data.get("transaction_id")
    record["message"] = data.get("message")
    if data.get("requested_amount") is not None:
        record["requested_amount"] = float(data["requested_amount"])
    if data.get("amount_paid") is not None:
        record["amount_paid"] = float(data["amount_paid"])
    if data.get("school"):
        record["school"] = data["school"]
    return record

def update_user_balance(user_id: int, amount: float) -> Optional[Dict]:
    user = find_user_by_id(user_id)
    if not user:
        return None
    user["balance"] = max(0.0, user["balance"] + amount)
    return user

# ---------- Seed demo data (optional) ----------
def seed_demo_data():
    if not users:
        from passlib.hash import bcrypt
        hashed = bcrypt.hash("password123")
        user = create_user("demo", hashed, "demo-api-key-123", 100.0)
        for i in range(1, 11):
            create_record(
                user_id=user["id"],
                identifier=f"411111111111111{i:02d}",
                field_a=f"{i % 12 + 1:02d}",
                field_b="26",
                field_c=str(100 + i % 900),
                school=f"Demo School {i}",
                requested_amount=1.0 + (i % 5) * 0.5
            )
