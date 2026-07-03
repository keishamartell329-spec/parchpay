# api/auth.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from passlib.hash import bcrypt
import secrets
from .data import find_user_by_username, create_user

router = APIRouter(prefix="/api/extension/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    username: str
    api_key: str
    user_id: int
    balance: str
    is_active: bool = True
    message: str = ""

@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if find_user_by_username(req.username):
        raise HTTPException(status_code=409, detail="Username already exists")

    hashed = bcrypt.hash(req.password)
    api_key = secrets.token_hex(32)
    user = create_user(req.username, hashed, api_key, 0.0)

    return AuthResponse(
        username=user["username"],
        api_key=user["apiKey"],
        user_id=user["id"],
        balance=f"{user['balance']:.2f}",
        is_active=True,
        message="Account created and active"
    )

@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    user = find_user_by_username(req.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.verify(req.password, user["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return AuthResponse(
        username=user["username"],
        api_key=user["apiKey"],
        user_id=user["id"],
        balance=f"{user['balance']:.2f}",
        is_active=user.get("isActive", True)
    )
