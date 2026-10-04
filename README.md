# SRS Reviewer — README

## Project: SRS Reviewer (CS325, GIKI)

An agentic web application that automatically analyzes Software Requirements Specifications (SRS) and PlantUML diagrams submitted by student teams, and reports quality defects to instructors.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy, SQLite |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui |
| LLM | Groq (free tier) — `llama3-8b-8192` |
| Auth | JWT (python-jose + passlib/bcrypt) |
| Containerization | Docker + docker compose |

---

## Quick Start (Manual, No Docker)

### 1. Backend

```powershell
cd backend

# Create and activate a virtual environment (recommended)
python -m venv venv
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure your Groq API key
# Edit backend/.env and set: GROQ_API_KEY=your_key_here

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs available at: http://localhost:8000/docs

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

App available at: http://localhost:5173

---

## Quick Start (Docker)

```powershell
# From project root
docker compose up --build
```

---

## Project Structure

```
SE_Project/
├── backend/
│   ├── app/
│   │   ├── api/              # Route handlers (auth, assignments, submissions, reports)
│   │   ├── core/             # Config, database, security, deps
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── llm/              # LLM engine, Groq adapter, mock adapter
│   │   ├── pipeline/
│   │   │   ├── srs/          # DOCX/PDF parser
│   │   │   ├── uml/          # PlantUML parser → internal model
│   │   │   ├── checks/       # Deterministic + LLM-assisted checks
│   │   │   └── traceability/ # Trace link suggestion + validation
│   │   └── main.py           # FastAPI app entry point
│   ├── config.yaml           # Rules, severities, ambiguity lexicon, score weights
│   ├── .env                  # Secrets (GROQ_API_KEY, SECRET_KEY, etc.)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/       # Layout, UI components (shadcn/ui style)
│       ├── pages/            # Login, Register, Dashboard, Assignments, Report, etc.
│       ├── lib/              # API client (Axios), Auth context, utils
│       └── App.tsx           # Router + AuthProvider
├── docker-compose.yml
├── run_backend.ps1
├── run_frontend.ps1
└── README.md
```

---

## Implemented Features (Tier 1 MVP)

### Authentication (FR-101 to FR-104)
- Register with name, email, password, role (student/instructor)
- JWT login, role-based access enforced server-side

### Assignments & Submissions (FR-201 to FR-207)
- Instructors create assignments
- Students create submissions, upload SRS (.docx/.pdf ≤ 20MB), upload UML (PlantUML .puml)
- File type validation with clear error messages
- Version tracking per submission

### SRS Parsing (FR-301 to FR-303, FR-305)
- Section hierarchy extraction
- Requirement extraction (identifier, text, section, class: functional/non-functional)
- Warning when no "shall" statements found

### Deterministic Requirement Checks
| Requirement | Check |
|---|---|
| FR-401 | Ambiguous words (configurable lexicon) |
| FR-402 | Multiple "shall" (non-atomic) |
| FR-405 | Missing IEEE template sections |
| FR-409 | Requirements without identifiers |
| FR-410 | Duplicate identifiers |
| FR-411 | NFRs without numeric thresholds/units |

### LLM-Assisted Checks (Groq)
| Requirement | Check |
|---|---|
| FR-403 | Testability assessment |
| FR-404 | Conflict detection between requirement pairs |

### UML Analysis (FR-501, FR-504, FR-601 to FR-609)
- PlantUML parser for use case, class, and sequence diagrams
- FR-601: Disconnected actors
- FR-602: Disconnected use cases
- FR-603: Empty classes
- FR-604: Associations without multiplicity
- FR-605: References to undefined classes
- FR-606: Sequence messages calling undefined operations
- FR-609: Duplicate element names

### Traceability (FR-701 to FR-709)
- Automatic link suggestion: requirement → use case → sequence → class
- User confirm/reject/create trace links
- Traceability matrix with CSV export
- Findings for: unlinked requirements, unlinked use cases, unlinked sequence diagrams

### Findings & Reports (FR-801, FR-802, FR-804 to FR-806, FR-809)
- Severity: Critical / Major / Minor
- Quality scores: Requirements (40%), UML (30%), Traceability (30%)
- Instructor accept/reject findings with comments
- Results visible to student team after instructor review

### Infrastructure (FR-901 to FR-906, NFR-06, NFR-07)
- config.yaml: rules, severities, lexicon, weights — loaded at startup
- Provider interface: Groq adapter + mock adapter
- LLM caching (in-memory, keyed by SHA-256 of prompt)
- LLM call logging (provider, model, tokens, latency, cache hit)
- PII redaction before LLM calls (emails, student IDs, proper names)
- Retry logic (up to 3 attempts on LLM failure)

---

## Configuration

Edit `backend/config.yaml` to customize:
- `rules.ambiguous_words.lexicon` — words that trigger FR-401
- `rules.*.severity` — critical / major / minor per rule
- `rubric` — score weights (must sum to 100)
- `expected_sections` — sections checked for FR-405

Edit `backend/.env`:
- `GROQ_API_KEY` — your Groq API key (get free at https://console.groq.com)
- `LLM_PROVIDER` — `groq` or `mock`
- `SECRET_KEY` — generate with: `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Team Responsibilities

| Area | Files |
|---|---|
| SRS & NLP | `backend/app/pipeline/srs/`, `backend/app/pipeline/checks/srs_checks.py`, `backend/app/pipeline/checks/llm_checks.py` |
| UML | `backend/app/pipeline/uml/`, `backend/app/pipeline/checks/uml_checks.py` |
| Traceability & Backend | `backend/app/pipeline/traceability/`, `backend/app/pipeline/analyzer.py`, `backend/app/api/` |
| Frontend & Instructor UI | `frontend/src/pages/`, `frontend/src/components/` |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Register user |
| POST | `/auth/login` | Login → JWT |
| GET | `/auth/me` | Current user |
| GET/POST | `/assignments` | List/create assignments |
| GET | `/assignments/{id}` | Get assignment |
| POST | `/submissions` | Create submission |
| POST | `/submissions/{id}/upload-srs` | Upload SRS file |
| POST | `/submissions/{id}/upload-uml` | Upload UML file |
| POST | `/submissions/{id}/analyze` | Trigger analysis |
| GET | `/submissions` | List submissions |
| GET | `/submissions/{id}` | Get submission detail |
| GET | `/reports/{id}/findings` | Get findings |
| GET | `/reports/{id}/scores` | Get quality scores |
| GET | `/reports/{id}/traceability` | Get trace links |
| GET | `/reports/{id}/traceability/csv` | Export CSV |
| POST | `/reports/{id}/findings/{fid}/decision` | Instructor decision |
| PUT | `/reports/{id}/trace-links/{lid}` | Update trace link |
| POST | `/reports/{id}/trace-links` | Create trace link |

Full interactive docs: http://localhost:8000/docs
