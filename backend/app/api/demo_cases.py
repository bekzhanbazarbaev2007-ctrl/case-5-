from fastapi import APIRouter
import json
import os

router = APIRouter()

@router.get("/demo-cases")
async def get_demo_cases():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
    path = os.path.join(data_dir, "demo_cases.json")
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)