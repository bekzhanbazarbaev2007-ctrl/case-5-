import json
import os
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
from app.models.schemas import AnalyzeRequest, AnalyzeResponse, IssueResult

# Load categories config
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")

def load_categories() -> List[dict]:
    path = os.path.join(DATA_DIR, "categories.json")
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def load_recipients() -> dict:
    path = os.path.join(DATA_DIR, "recipients.json")
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def detect_language(text: str) -> str:
    """Simple heuristic language detection for Kazakh/Russian."""
    kk_specific = set("äğqñöüúíh")
    # Also check Kazakh Cyrillic-specific letters
    kk_cyrillic = set("әғқңөүұіһ")
    text_lower = text.lower()
    kk_count = sum(1 for c in text_lower if c in kk_cyrillic or c in kk_specific)
    if kk_count >= 2 or any(w in text_lower for w in ["бар", "жок", "деген", "туспеди", "жерим", "болды", "жардемакы", "отиниш", "жерiмнiн", "жеримнин"]):
        return "kk"
    return "ru"

def normalize_text(text: str) -> str:
    """Basic normalization: lowercase, strip extra spaces, unify Kazakh variants."""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    # Unify common Kazakh spelling variants for matching
    replacements = {
        'ә': 'а', 'і': 'и', 'ң': 'н', 'ғ': 'г', 'ү': 'у', 'ұ': 'у', 'ө': 'о', 'һ': 'х',
        'ё': 'е', 'э': 'е',
    }
    return text

def normalize_for_match(text: str) -> str:
    """Aggressive normalization for keyword matching (typos, Kazakh variants)."""
    text = normalize_text(text)
    # Strip diacritics for fuzzy match
    for src, dst in [('ә', 'а'), ('і', 'и'), ('ң', 'н'), ('ғ', 'г'), ('ү', 'у'), ('ұ', 'у'), ('ө', 'о'), ('һ', 'х')]:
        text = text.replace(src, dst)
    return text

def get_confidence_label(confidence: float) -> Tuple[str, str]:
    if confidence >= 0.90:
        return ("Жоғары сенімділік", "Высокая уверенность")
    elif confidence >= 0.70:
        return ("Орташа сенімділік", "Средняя уверенность")
    else:
        return ("Қосымша нақтылау қажет", "Требуется уточнение")

def get_status(confidence: float, needs_clarification: bool) -> str:
    if needs_clarification or confidence < 0.70:
        return "needs_clarification"
    return "routed"


class RoutingEngine(ABC):
    @abstractmethod
    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        pass


class MockRoutingEngine(RoutingEngine):
    """Deterministic keyword-based routing engine for offline/demo mode."""

    def __init__(self):
        self.categories = load_categories()
        self.recipients = load_recipients()

    def _find_matching_categories(self, text_normalized: str) -> List[Tuple[dict, float, List[str]]]:
        """Returns list of (category, confidence, matched_keywords)."""
        matches = []
        text_fuzzy = normalize_for_match(text_normalized)
        text_words = set(re.split(r'[\s,;.!?]+', text_fuzzy))

        for cat in self.categories:
            if cat["id"] == "other":
                continue
            all_keywords = [normalize_for_match(k) for k in cat["keywords_kk"] + cat["keywords_ru"]]
            matched = []
            for kw in all_keywords:
                if not kw or len(kw) < 3:
                    continue
                if kw in text_fuzzy or kw in text_normalized:
                    matched.append(kw)
                elif len(kw) >= 4 and any(kw in w for w in text_words if len(w) >= len(kw)):
                    matched.append(kw)

            if matched:
                raw_score = min(len(matched) * 0.18 + 0.62, 0.97)
                if len(matched) == 1:
                    raw_score = min(raw_score, 0.85)
                matches.append((cat, round(raw_score, 2), matched))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def _split_into_segments(self, text: str) -> List[str]:
        """Try to split text into separate issue segments."""
        parts = re.split(r'(?<=[.!?])\s+', text)
        if len(parts) <= 1:
            connectors = [
                r'\bтакже\b', r'\bеще\b', r'\bещё\b', r'\bа ещё\b', r'\bа еще\b',
                r'\bсонымен\s+катар\b', r'\bсондай-ақ\b', r'\bсондай-ак\b',
                r'\bжәне\b', r'\bи\b', r'\bболее того\b'
            ]
            for pattern in connectors:
                parts = re.split(pattern, text, flags=re.IGNORECASE)
                if len(parts) > 1:
                    break
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 5]
        return parts if parts else [text]

    def _get_clarification_questions(self, category_id: str, lang: str) -> List[str]:
        questions = {
            "land": [
                "Жер учаскесінін орналаскан ауданын корсетіңіз / Укажите район расположения земельного участка",
                "Маселе жер учаскесін тіркеуге катысты ма? / Проблема связана с оформлением?"
            ],
            "social": [
                "Жардемакынын кай турі? / Какой вид пособия?",
                "Маселе тагайындауга катысты ма, акше толемге ме? / Назначение или задержка выплаты?"
            ],
            "housing": [
                "Маселе жалдамалы турын уйге катысты ма, жеке мулікке ме? / Вопрос касается арендного или собственного жилья?"
            ],
            "health": [
                "Шагым ауруханага катысты ма, дарігерге ме? / Жалоба на больницу или на конкретного врача?"
            ],
            "other": [
                "Отінішінізді накtырак сипаттай аласыз ба? / Можете описать проблему подробнее?"
            ]
        }
        return questions.get(category_id, questions["other"])

    def _build_issue(self, segment: str, cat: dict, confidence: float,
                     matched_kw: List[str], issue_num: int, lang: str) -> IssueResult:
        label_kk, label_ru = get_confidence_label(confidence)
        needs_clarification = confidence < 0.70

        recipient = self.recipients.get(cat["id"], {"name": "Жергілікті аткарушы орган / Местный исполнительный орган"})

        kw_str = ", ".join(matched_kw[:3])
        reason_kk = f"Мәтінде «{kw_str}» тірек сөздері анықталды. Сондықтан өтініш «{cat['name_kk']}» бағытына алдын ала ұсынылды."
        reason_ru = f"В тексте обнаружены ключевые слова «{kw_str}», поэтому обращение предварительно отнесено к направлению «{cat['name_ru']}»."

        clarification_qs = []
        if needs_clarification:
            clarification_qs = self._get_clarification_questions(cat["id"], lang)

        return IssueResult(
            issue_number=issue_num,
            original_text=segment,
            normalized_text=normalize_text(segment),
            category=cat["id"],
            category_kk=cat["name_kk"],
            category_ru=cat["name_ru"],
            recommended_recipient=recipient.get("name", "Жергілікті аткарушы орган"),
            confidence=confidence,
            confidence_label_kk=label_kk,
            confidence_label_ru=label_ru,
            reason_kk=reason_kk,
            reason_ru=reason_ru,
            needs_clarification=needs_clarification,
            clarification_questions=clarification_qs,
            status=get_status(confidence, needs_clarification)
        )

    def _find_best_segment(self, cat: dict, segments: List[str], full_text: str) -> str:
        cat_kws = [normalize_for_match(k) for k in cat["keywords_kk"] + cat["keywords_ru"]]
        for seg in segments:
            seg_fuzzy = normalize_for_match(seg)
            if any(kw in seg_fuzzy for kw in cat_kws if kw):
                return seg
        return full_text

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        text = request.text.strip()
        lang = detect_language(text)
        normalized = normalize_text(text)

        segments = self._split_into_segments(text)

        # Collect matches from full text AND each segment for multi-intent
        category_matches: Dict[str, Tuple[dict, float, List[str], str]] = {}

        for seg in segments:
            seg_matches = self._find_matching_categories(normalize_text(seg))
            for cat, conf, kw in seg_matches:
                cid = cat["id"]
                if cid not in category_matches or conf > category_matches[cid][1]:
                    category_matches[cid] = (cat, conf, kw, seg)

        if not category_matches:
            all_matches = self._find_matching_categories(normalized)
            for cat, conf, kw in all_matches:
                category_matches[cat["id"]] = (cat, conf, kw, text)

        issues = []
        sorted_matches = sorted(category_matches.values(), key=lambda x: x[1], reverse=True)

        # Filter weak single-keyword matches when stronger matches exist
        if len(sorted_matches) > 1:
            top_conf = sorted_matches[0][1]
            sorted_matches = [m for m in sorted_matches if m[1] >= 0.70 or len(m[2]) >= 2 or m[1] >= top_conf - 0.15]

        if sorted_matches:
            for i, (cat, conf, kw, seg) in enumerate(sorted_matches[:4]):
                best_segment = self._find_best_segment(cat, segments, text)
                issue = self._build_issue(best_segment if best_segment else seg, cat, conf, kw, i + 1, lang)
                issues.append(issue)
        else:
            other_cat = next((c for c in self.categories if c["id"] == "other"), {
                "id": "other", "name_kk": "Баска", "name_ru": "Другое",
                "keywords_kk": [], "keywords_ru": []
            })
            label_kk, label_ru = get_confidence_label(0.45)
            issues.append(IssueResult(
                issue_number=1,
                original_text=text,
                normalized_text=normalized,
                category="other",
                category_kk="Баска",
                category_ru="Другое",
                recommended_recipient="Жергілікті акімдік / Местная администрация (акимат)",
                confidence=0.45,
                confidence_label_kk=label_kk,
                confidence_label_ru=label_ru,
                reason_kk="Отінішті автоматты турде жіктеу мумкін болмады. Адам операторына жіберу усынылады.",
                reason_ru="Автоматическая классификация не удалась. Рекомендуется передача оператору.",
                needs_clarification=True,
                clarification_questions=["Отінішінізді накtырак сипаттай аласыз ба? / Можете описать проблему подробнее?"],
                status="needs_clarification"
            ))

        overall_confidence = sum(i.confidence for i in issues) / len(issues) if issues else 0.5
        needs_human_review = overall_confidence < 0.70 or any(i.needs_clarification for i in issues)

        return AnalyzeResponse(
            language=lang,
            issues=issues,
            overall_confidence=round(overall_confidence, 2),
            needs_human_review=needs_human_review,
            used_mock=True
        )


class LLMRoutingEngine(RoutingEngine):
    """LLM-based routing engine using Gemini API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.mock_engine = MockRoutingEngine()
        self.categories = load_categories()

    def _build_system_prompt(self) -> str:
        cats = self.categories
        cat_list = "\n".join([f"- {c['id']}: {c['name_kk']} / {c['name_ru']}" for c in cats])
        return f"""You are an AI assistant helping route citizen requests to the correct Kazakhstan government authority.
This is a PRELIMINARY ROUTING ASSISTANT only - not an official government decision-maker.

Available categories:
{cat_list}

Rules:
- Detect ALL issues in the text (may be multiple)
- Support Kazakh and Russian (including typos and mixed language)
- Return structured JSON only
- Be conservative with confidence - never claim 100%
- Never invent government contacts or laws
- Frame all results as preliminary recommendations

Return JSON in this exact format:
{{
  "language": "kk" or "ru" or "mixed",
  "issues": [
    {{
      "original_text": "...",
      "normalized_text": "...",
      "category": "category_id",
      "recommended_recipient": "...",
      "confidence": 0.85,
      "reason_kk": "...",
      "reason_ru": "...",
      "needs_clarification": false,
      "clarification_questions": []
    }}
  ],
  "overall_confidence": 0.85,
  "needs_human_review": false
}}"""

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        import httpx
        import json as json_mod

        try:
            prompt = f"Analyze this citizen request and route it to appropriate government authorities:\n\n\"{request.text}\"\n\nReturn valid JSON only."

            response = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}",
                json={
                    "contents": [{"parts": [{"text": self._build_system_prompt() + "\n\n" + prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000}
                },
                timeout=30.0
            )

            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code}")

            result = response.json()
            text_resp = result["candidates"][0]["content"]["parts"][0]["text"]

            json_match = re.search(r'\{.*\}', text_resp, re.DOTALL)
            if not json_match:
                raise Exception("No JSON found in response")

            data = json_mod.loads(json_match.group())

            issues = []
            cat_map = {c["id"]: c for c in self.categories}
            recipients = load_recipients()

            for i, issue_data in enumerate(data.get("issues", [])):
                cat_id = issue_data.get("category", "other")
                cat = cat_map.get(cat_id, cat_map.get("other", {"id": "other", "name_kk": "Баска", "name_ru": "Другое"}))
                confidence = float(issue_data.get("confidence", 0.5))
                label_kk, label_ru = get_confidence_label(confidence)
                needs_clar = issue_data.get("needs_clarification", confidence < 0.70)

                issues.append(IssueResult(
                    issue_number=i+1,
                    original_text=issue_data.get("original_text", request.text),
                    normalized_text=issue_data.get("normalized_text", normalize_text(request.text)),
                    category=cat_id,
                    category_kk=cat.get("name_kk", "Баска"),
                    category_ru=cat.get("name_ru", "Другое"),
                    recommended_recipient=issue_data.get("recommended_recipient",
                        recipients.get(cat_id, {}).get("name", "Жергілікті аткарушы орган")),
                    confidence=confidence,
                    confidence_label_kk=label_kk,
                    confidence_label_ru=label_ru,
                    reason_kk=issue_data.get("reason_kk", ""),
                    reason_ru=issue_data.get("reason_ru", ""),
                    needs_clarification=needs_clar,
                    clarification_questions=issue_data.get("clarification_questions", []),
                    status=get_status(confidence, needs_clar)
                ))

            overall = float(data.get("overall_confidence", 0.5))
            return AnalyzeResponse(
                language=data.get("language", "ru"),
                issues=issues,
                overall_confidence=round(overall, 2),
                needs_human_review=data.get("needs_human_review", overall < 0.70),
                used_mock=False
            )

        except Exception as e:
            print(f"LLM routing failed: {e}, falling back to mock engine")
            result = self.mock_engine.analyze(request)
            result.used_mock = True
            return result


def get_routing_engine() -> RoutingEngine:
    """Factory function - returns LLM engine if API key available, else mock."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key:
        return LLMRoutingEngine(api_key)
    return MockRoutingEngine()