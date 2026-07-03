# api/index.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .auth import router as auth_router
from .records import router as records_router
from .data import seed_demo_data

app = FastAPI()

# CORS (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(auth_router)
app.include_router(records_router)

@app.get("/")
async def root():
    return {"message": "QueuePay API is running."}

# Seed demo data on startup
seed_demo_data()

# For Vercel, export `app` (already named)
