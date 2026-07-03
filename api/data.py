# api/data.py
import os
import time
from typing import Optional, Dict, List, Any
from passlib.hash import bcrypt

# Try to import asyncpg; if it fails, we'll use in-memory store
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

# Global in-memory stores (fallback)
_users = []
_records = []
_pool = None

async def get_pool():
    """Return asyncpg connection pool if available and DATABASE_URL set, else None."""
    global _pool
    if not ASYNCPG_AVAILABLE:
        return None
    if _pool is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            return None
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=10,
            command_timeout=10
        )
    return _pool

# ---------- Helper to determine if we're using DB ----------
async def using_database() -> bool:
    pool = await get_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
            return True
    except:
        return False

# ---------- User helpers (with fallback) ----------
async def find_user_by_api_key(api_key: str) -> Optional[Dict]:
    pool = await get_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id, username, passwordhash, apikey, balance, isactive FROM users WHERE apikey = $1",
                    api_key
                )
                if row:
                    return {
                        "id": row["id"],
                        "username": row["username"],
                        "passwordHash": row["passwordhash"],
                        "apiKey": row["apikey"],
                        "balance": float(row["balance"]),
                        "isActive": row["isactive"]
                    }
        except:
            pass
    # Fallback to in-memory
    for user in _users:
        if user["apiKey"] == api_key:
            return user
    return None

async def find_user_by_username(username: str) -> Optional[Dict]:
    pool = await get_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id, username, passwordhash, apikey, balance, isactive FROM users WHERE username = $1",
                    username
                )
                if row:
                    return {
                        "id": row["id"],
                        "username": row["username"],
                        "passwordHash": row["passwordhash"],
                        "apiKey": row["apikey"],
                        "balance": float(row["balance"]),
                        "isActive": row["isactive"]
                    }
        except:
            pass
    # Fallback to in-memory
    for user in _users:
        if user["username"] == username:
            return user
    return None

async def find_user_by_id(user_id: int) -> Optional[Dict]:
    pool = await get_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id, username, passwordhash, apikey, balance, isactive FROM users WHERE id = $1",
                    user_id
                )
                if row:
                    return {
                        "id": row["id"],
                        "username": row["username"],
                        "passwordHash": row["passwordhash"],
                        "apiKey": row["apikey"],
                        "balance": float(row["balance"]),
                        "isActive": row["isactive"]
                    }
        except:
            pass
    # Fallback to in-memory
    for user in _users:
        if user["id"] == user_id:
            return user
    return None

async def create_user(username: str, password_hash: str, api_key: str, balance: float = 0.0) -> Dict:
    pool = await get_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """INSERT INTO users (username, passwordhash, apikey, balance, isactive)
                       VALUES ($1, $2, $3, $4, true)
                       RETURNING id, username, passwordhash, apikey, balance, isactive""",
                    username, password_hash, api_key, balance
                )
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "passwordHash": row["passwordhash"],
                    "apiKey": row["apikey"],
                    "balance": float(row["balance"]),
                    "isActive": row["isactive"]
                }
        except:
            pass
    # Fallback to in-memory
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
    pool = await get_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "UPDATE users SET balance = balance + $1 WHERE id = $2 RETURNING id, username, balance",
                    amount, user_id
                )
                if row:
                    return {
                        "id": row["id"],
                        "username": row["username"],
                        "balance": float(row["balance"])
                    }
        except:
            pass
    # Fallback to in-memory
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
    pool = await get_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """INSERT INTO records (userid, identifier, field_a, field_b, field_c, school, requested_amount, status, created_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', NOW())
                       RETURNING id, userid, identifier, field_a, field_b, field_c, school, requested_amount, status, transaction_id, message, amount_paid, created_at""",
                    user_id, identifier, field_a, field_b, field_c, school, requested_amount
                )
                return dict(row)
        except:
            pass
    # Fallback to in-memory
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
    pool = await get_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                # Build dynamic SET clause
                sets = []
                params = []
                idx = 1
                for key in ("status", "transaction_id", "message", "requested_amount", "amount_paid", "school"):
                    if key in data:
                        sets.append(f"{key} = ${idx}")
                        params.append(data[key])
                        idx += 1
                if not sets:
                    return None
                params.extend([record_id, user_id])
                query = f"""UPDATE records SET {', '.join(sets)} 
                            WHERE id = ${idx} AND userid = ${idx+1}
                            RETURNING id, userid, identifier, field_a, field_b, field_c, school, requested_amount, status, transaction_id, message, amount_paid, created_at"""
                row = await conn.fetchrow(query, *params)
                if row:
                    return dict(row)
        except:
            pass
    # Fallback to in-memory
    for rec in _records:
        if rec["id"] == record_id and rec["userid"] == user_id:
            for key in ("status", "transaction_id", "message", "requested_amount", "amount_paid", "school"):
                if key in data:
                    rec[key] = data[key]
            return rec
    return None

async def get_next_record_for_user(user_id: int, requested_amount: Optional[float] = None) -> Optional[Dict]:
    pool = await get_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                # 1. Try successful record with amount
                if requested_amount is not None:
                    row = await conn.fetchrow(
                        """SELECT id, userid, identifier, field_a, field_b, field_c, school, requested_amount, status, transaction_id, message, amount_paid, created_at
                           FROM records WHERE userid = $1 AND status = 'success' AND requested_amount = $2
                           ORDER BY created_at DESC LIMIT 1""",
                        user_id, requested_amount
                    )
                    if row:
                        return dict(row)
                # 2. Try pending
                row = await conn.fetchrow(
                    """SELECT id, userid, identifier, field_a, field_b, field_c, school, requested_amount, status, transaction_id, message, amount_paid, created_at
                       FROM records WHERE userid = $1 AND status = 'pending'
                       ORDER BY id LIMIT 1""",
                    user_id
                )
                if row:
                    return dict(row)
                # 3. Fallback to any successful
                row = await conn.fetchrow(
                    """SELECT id, userid, identifier, field_a, field_b, field_c, school, requested_amount, status, transaction_id, message, amount_paid, created_at
                       FROM records WHERE userid = $1 AND status = 'success'
                       ORDER BY created_at DESC LIMIT 1""",
                    user_id
                )
                if row:
                    return dict(row)
        except:
            pass
    # Fallback to in-memory
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
    pool = await get_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT id, username, balance, apikey, isactive FROM users ORDER BY id")
                return [dict(row) for row in rows]
        except:
            pass
    # Fallback to in-memory
    return [{"id": u["id"], "username": u["username"], "balance": u["balance"], "apikey": u["apiKey"], "isactive": u["isActive"]} for u in _users]

async def get_all_records() -> List[Dict]:
    pool = await get_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM records ORDER BY id")
                return [dict(row) for row in rows]
        except:
            pass
    # Fallback to in-memory
    return _records

# ---------- Database initialization (if available) ----------
async def init_db():
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    passwordhash TEXT NOT NULL,
                    apikey TEXT UNIQUE NOT NULL,
                    balance DECIMAL(10,2) DEFAULT 0.0,
                    isactive BOOLEAN DEFAULT TRUE
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id SERIAL PRIMARY KEY,
                    userid INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    identifier TEXT NOT NULL,
                    field_a TEXT NOT NULL,
                    field_b TEXT NOT NULL,
                    field_c TEXT NOT NULL,
                    school TEXT,
                    requested_amount DECIMAL(10,2),
                    status TEXT DEFAULT 'pending',
                    transaction_id TEXT,
                    message TEXT,
                    amount_paid DECIMAL(10,2),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_records_user_status ON records(userid, status)")
    except:
        pass

# ---------- Seed demo data ----------
async def seed_demo_data():
    # Check if any users exist (in-memory or DB)
    users = await get_all_users()
    if users:
        return

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
