from fastapi import APIRouter
from app.services.routing_engine import load_categories
from typing import List

router = APIRouter()

@router.get("/categories", response_model=List[dict])
async def get_categories():
    return load_categories()