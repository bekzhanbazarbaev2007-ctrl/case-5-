from pydantic import BaseModel, Field
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)

class IssueResult(BaseModel):
    issue_number: int
    original_text: str
    normalized_text: str
    category: str
    category_kk: str
    category_ru: str
    recommended_recipient: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_label_kk: str
    confidence_label_ru: str
    reason_kk: str
    reason_ru: str
    needs_clarification: bool
    clarification_questions: List[str] = []
    status: str  # "routed", "needs_clarification", "escalated"

class AnalyzeResponse(BaseModel):
    language: str
    issues: List[IssueResult]
    overall_confidence: float
    needs_human_review: bool
    disclaimer_kk: str = "Бул алдын ала усыныс болып табылады жане зангды шешім емес."
    disclaimer_ru: str = "Это предварительная рекомендация и не является официальным юридическим решением."
    used_mock: bool = False

class ClarifyRequest(BaseModel):
    text: str
    issue_category: Optional[str] = None

class ClarifyResponse(BaseModel):
    questions: List[str]

class Category(BaseModel):
    id: str
    name_kk: str
    name_ru: str
    keywords_kk: List[str]
    keywords_ru: List[str]
    recipients: List[str]

class DemoCase(BaseModel):
    id: int
    title_kk: str
    title_ru: str
    text: str
    language: str
    tags: List[str]

class DashboardData(BaseModel):
    total_analyzed: int
    high_confidence: int
    medium_confidence: int
    needs_clarification: int
    multi_intent: int
    language_distribution: dict
    category_distribution: dict
    disclaimer: str = "Demo analytics — not official government data"