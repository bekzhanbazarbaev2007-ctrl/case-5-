from fastapi import APIRouter
from app.models.schemas import ClarifyRequest, ClarifyResponse

router = APIRouter()

CLARIFICATION_QUESTIONS = {
    "land": [
        "Жер учаскесінін орналаскан ауданын корсетіңіз / Укажите район земельного участка",
        "Маселе жер учаскесін тіркеуге катысты ма? / Проблема связана с оформлением?"
    ],
    "social": [
        "Жардемакынын кай турі алынбады? / Какой вид пособия не поступил?",
        "Маселе тагайындауга катысты ма, акше толемге ме? / Это вопрос назначения или выплаты?"
    ],
    "housing": [
        "Турын уй жалдамалы ма, жеке меншік пе? / Жилье арендное или собственное?"
    ],
    "health": [
        "Шагым ауруханага катысты ма, жеке дарігерге ме? / Жалоба на больницу или врача?"
    ],
    "default": [
        "Отінішінізді толыгырак сипаттай аласыз ба? / Можете описать проблему подробнее?",
        "Маселе кай ауданда орын алды? / В каком районе возникла проблема?"
    ]
}

@router.post("/clarify", response_model=ClarifyResponse)
async def clarify(request: ClarifyRequest):
    category = request.issue_category or "default"
    questions = CLARIFICATION_QUESTIONS.get(category, CLARIFICATION_QUESTIONS["default"])
    return ClarifyResponse(questions=questions)