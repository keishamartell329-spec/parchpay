# api/data.py
import asyncpg
import os
from typing import Optional, List, Dict, Any
import time
from passlib.hash import bcrypt

# Database connection pool (created once)
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            os.environ.get("DATABASE_URL"),
            min_size=1,
            max_size=10
        )
    return _pool

# ---------- User helpers ----------
async def find_user_by_api_key(api_key: str) -> Optional[Dict]:
    pool = await get_pool()
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
        return None

async def find_user_by_username(username: str) -> Optional[Dict]:
    pool = await get_pool()
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
        return None

async def find_user_by_id(user_id: int) -> Optional[Dict]:
    pool = await get_pool()
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
        return None

async def create_user(username: str, password_hash: str, api_key: str, balance: float = 0.0) -> Dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO users (username, passwordhash, apikey, balance, isactive)
               VALUES ($1, $2, $3, $4, true) RETURNING id, username, passwordhash, apikey, balance, isactive""",
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

# ---------- Record helpers ----------
async def get_next_record_for_user(user_id: int, requested_amount: Optional[float] = None) -> Optional[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        # First try with amount filter if provided
        if requested_amount is not None:
            row = await conn.fetchrow(
                """SELECT id, userid, identifier, field_a, field_b, field_c, school, requested_amount, status, transaction_id, message, amount_paid, created_at
                   FROM records WHERE userid = $1 AND status NOT IN ('success', 'failed') AND requested_amount = $2
                   ORDER BY id LIMIT 1""",
                user_id, requested_amount
            )
            if row:
                return dict(row)
        # Fallback: any pending record
        row = await conn.fetchrow(
            """SELECT id, userid, identifier, field_a, field_b, field_c, school, requested_amount, status, transaction_id, message, amount_paid, created_at
               FROM records WHERE userid = $1 AND status NOT IN ('success', 'failed')
               ORDER BY id LIMIT 1""",
            user_id
        )
        if row:
            return dict(row)
        return None

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
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO records (userid, identifier, field_a, field_b, field_c, school, requested_amount, status, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', NOW())
               RETURNING id, userid, identifier, field_a, field_b, field_c, school, requested_amount, status, transaction_id, message, amount_paid, created_at""",
            user_id, identifier, field_a, field_b, field_c, school, requested_amount
        )
        return dict(row)

async def update_record_status(record_id: int, user_id: int, data: Dict) -> Optional[Dict]:
    pool = await get_pool()
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
        params.append(record_id)
        params.append(user_id)
        query = f"""UPDATE records SET {', '.join(sets)} 
                    WHERE id = ${idx} AND userid = ${idx+1}
                    RETURNING id, userid, identifier, field_a, field_b, field_c, school, requested_amount, status, transaction_id, message, amount_paid, created_at"""
        row = await conn.fetchrow(query, *params)
        if row:
            return dict(row)
        return None

async def update_user_balance(user_id: int, amount: float) -> Optional[Dict]:
    pool = await get_pool()
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
        return None

# ---------- Admin helpers ----------
async def get_all_users():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, username, balance, apikey, isactive FROM users ORDER BY id")
        return [dict(row) for row in rows]

async def get_all_records():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM records ORDER BY id")
        return [dict(row) for row in rows]

# ---------- Database initialization ----------
async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Create users table
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
        # Create records table
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

# ---------- Seed demo data (only if no users exist) ----------
async def seed_demo_data():
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if users exist
        count = await conn.fetchval("SELECT COUNT(*) FROM users")
        if count > 0:
            return
        # Create demo user
        hashed = bcrypt.hash("password123")
        user = await create_user("demo", hashed, "demo-api-key-123", 100.0)
        # Insert 10 demo records
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
