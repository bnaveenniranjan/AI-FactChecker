# AI Government Scheme Fact Checker

A full-stack Django application that lets users search for Indian government schemes and receive chronological, source-backed, AI-synthesised information — powered by the **Google Gemini API**.

---

## Quick Start

### 1. Clone & install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your-key-here
```

### 3. Apply migrations
```bash
python manage.py migrate
```

### 4. Create superuser (admin panel)
```bash
python manage.py createsuperuser
```

### 5. Start the development server
```bash
python manage.py runserver
```

- **API base**: http://localhost:8000/api/
- **Admin panel**: http://localhost:8000/admin/
- **Browsable API**: http://localhost:8000/api/v1/schemes/

---

## API Endpoints (v1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/research/` | Research a government scheme |
| `GET` | `/api/v1/research/{id}/` | Get research job status + result |
| `GET` | `/api/v1/schemes/` | List / search schemes |
| `GET` | `/api/v1/schemes/{id}/` | Scheme detail |
| `GET` | `/api/v1/schemes/{id}/timeline/` | Chronological timeline |
| `GET` | `/api/v1/schemes/{id}/budgets/` | Budget history |
| `GET` | `/api/v1/schemes/{id}/leadership/` | Leadership history |
| `POST` | `/api/v1/fact-check/` | Verify a factual claim |
| `GET` | `/api/v1/sources/{id}/` | Source metadata |

### Example: Research a scheme
```bash
curl -X POST http://localhost:8000/api/v1/research/ \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain PM-KISAN from its launch to the present"}'
```

### Example: Fact-check a claim
```bash
curl -X POST http://localhost:8000/api/v1/fact-check/ \
  -H "Content-Type: application/json" \
  -d '{"claim": "PM-KISAN provides ₹6000 per year to farmers"}'
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

All 55 tests run without live API calls (Gemini and HTTP are mocked).

---

## Project Structure

```
AI FactChecker/
├── manage.py
├── fact_checker/           # Django project (settings, urls, wsgi)
├── apps/
│   ├── schemes/            # Scheme, SchemeAlias, SchemeBenefit, EligibilityRule
│   ├── leadership/         # PoliticalParty, Government, Leader, MinisterialTenure
│   ├── budgets/            # BudgetRecord (BE / RE / Actual — never mixed)
│   ├── sources/            # Source, EvidenceExcerpt, retrieval connectors
│   ├── timeline/           # TimelineEvent, SchemeAmendment
│   ├── factcheck/          # Claim, ClaimEvidence, FactCheckResult
│   ├── ai_service/         # GeminiClient, Pydantic schemas, prompt templates
│   ├── search/             # ResearchJob, ResearchCache, orchestrator
│   └── api/                # DRF serializers, views, URLs
├── tests/
│   ├── test_schemes.py
│   ├── test_budgets.py
│   ├── test_sources.py
│   ├── test_ai_client.py
│   └── test_api.py
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Gemini receives evidence, not questions** | AI synthesises retrieved sources — it never invents facts |
| **SSRF protection via domain allowlist** | All external fetches are restricted to `ALLOWED_DOMAINS` |
| **BE / RE / Actual are separate DB fields** | Budget figures are never treated as interchangeable |
| **Timeline events are immutable history** | Amendments create new records, never overwrite old ones |
| **Contradicting sources are never removed** | When sources disagree, both versions are stored and shown |
| **`insufficient_evidence` ≠ `false`** | Missing evidence does not equal a false claim |
| **Single `GeminiClient` module** | All AI calls go through one abstraction — swap provider without rewriting logic |

---

## Adding Your Gemini API Key

1. Get a key at https://aistudio.google.com/app/apikey
2. Open `.env` and set `GEMINI_API_KEY=your-key-here`
3. The key is **never** logged, exposed in API responses, or committed to git

---

## Phases Completed

- ✅ Phase 1: Architecture, DB design, API contracts
- ✅ Phase 2: All Django models + admin + migrations + tests
- ✅ Phase 3: Source connectors (WebConnector, PIBConnector) + SSRF protection
- ✅ Phase 4: Source retrieval, evidence storage, deduplication
- ✅ Phase 5: Gemini integration, structured output, schema validation
- ✅ Phase 6: Timeline, leadership, budget endpoints
- ✅ Phase 7: REST API — all 9 v1 endpoints

**Next phases:** Frontend (React/TypeScript), Celery async jobs, charts, caching hardening.
