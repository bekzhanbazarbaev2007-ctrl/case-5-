from fastapi import APIRouter
from app.db.database import get_dashboard_stats

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard():
    return get_dashboard_stats()