from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import analyze, categories, demo_cases, dashboard, health, clarify
from app.db.database import init_db
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="AI-Otinish Navigator API",
    description="Kazakhstan citizen request routing assistant - Demo prototype",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(health.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(clarify.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(demo_cases.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
