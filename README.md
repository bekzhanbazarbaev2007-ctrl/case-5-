# AI-Otinish Navigator

**Demo prototype** — Kazakhstan citizen request routing assistant.

Analyzes free-form citizen requests in Kazakh and Russian, detects multiple issues, and provides preliminary routing recommendations to appropriate government directions.

> ⚠️ This is a demonstration prototype. Not an official government service. All routing data is synthetic/demo.

## Features

- **Multi-intent detection** — one request → multiple issues → multiple routes
- **Kazakh + Russian** support with typo tolerance
- **14 routing categories** (configurable via `data/categories.json`)
- **Confidence scoring** with clarification escalation
- **Replaceable AI engine** — works offline with MockRoutingEngine
- **Bilingual UI** with language switcher
- **Demo mode** with 8 prepared test cases
- **Analytics dashboard** with demo statistics

## Architecture

```
Citizen text → Language detection → Normalization → Multi-intent extraction
→ Category classification → Recipient mapping → Confidence scoring → JSON response
```

**Stack**: FastAPI (Python) + Next.js 14 (TypeScript) + SQLite + Tailwind CSS

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Environment Variables

```env
# Optional — app works without it using MockRoutingEngine
GEMINI_API_KEY=

# App settings
APP_ENV=development
DB_PATH=./data/otinish.db
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze` | Analyze citizen text |
| POST | `/api/clarify` | Get clarification questions |
| GET | `/api/categories` | List categories |
| GET | `/api/demo-cases` | Demo test cases |
| GET | `/api/dashboard` | Analytics |
| GET | `/api/health` | Health check |

## Testing

```bash
# From project root
pip install -r backend/requirements.txt
pytest tests/ -v
```

## Demo Instructions

1. Open http://localhost:3000
2. Click any demo case card OR use "Тест мысалын жүктеу"
3. Click "Өтінішті талдау" / "Анализировать"
4. View detected issues with confidence, reasons, and routing
5. Visit `/dashboard` for analytics

**Recommended demo input:**
```
Сәлеметсіз бе. Менің жер учаскеме қатысты құжаттарымда проблема бар. Сонымен қатар осы айда жәрдемақым түспеді.
```
Expected: 2 issues (land + social protection)

## Limitations

- Keyword-based mock engine (not production ML)
- Demo recipient names (not official government contacts)
- No real government routing registry integration
- No authentication or audit logging
- Analytics uses seeded demo data
- LLM mode requires GEMINI_API_KEY (optional)

## Future Improvements

- Real government routing registry integration
- Vector search / RAG with official knowledge base
- District-level routing
- Speech-to-text input
- Human operator dashboard
- Model evaluation and feedback loop
- Telegram/WhatsApp integration

## License

Demo prototype for educational/hackathon purposes.
