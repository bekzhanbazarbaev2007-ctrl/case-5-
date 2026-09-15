from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.routing_engine import get_routing_engine
from app.db.database import save_analysis
import traceback

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="Text cannot be empty")
    try:
        engine = get_routing_engine()
        result = engine.analyze(request)
        try:
            save_analysis(request.text, result)
        except Exception:
            pass  # Non-critical
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.")