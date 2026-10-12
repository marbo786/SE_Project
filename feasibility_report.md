# Feasibility Report: SRS Reviewer (Automated Requirements & UML Quality Analysis Platform)

**Document Reference:** GIKI-FCSE-CS325-FR-2026-V1.0  
**Academic Context:** Ghulam Ishaq Khan Institute of Engineering Sciences and Technology, Faculty of Computer Science and Engineering  
**Course:** Software Engineering (CS325 / BS Computer Science, 5th Semester)  
**Author / Evaluator:** Senior Technical Analyst  
**Date:** October 10, 2026  

---

## Baseline Extraction & Documented Assumptions

The evaluation is based on the GIKI BS Computer Science 5th Semester Software Engineering course feasibility template and the empirical repository artifacts in the project workspace (`SE_Project`). Where the template defines blank placeholders, explicit values have been extracted from repository metadata or formally declared under **Assumptions**.

| Parameter | Extracted / Verified Fact | Source / Evidence |
| :--- | :--- | :--- |
| **Project Title** | **SRS Reviewer** (Automated SRS & UML Analyzer) | `README.md`, Commit history (`d311c5f`) |
| **Objectives** | Automated verification of SRS documents, PlantUML syntax/semantics, multi-tier traceability, and agentic LLM repair loop | Project architecture, `backend/config.yaml` |
| **Scope** | Ingestion of DOCX/PDF and PlantUML files; deterministic regex checks; LLM-assisted testability and conflict checks; Jaccard-based traceability; normalized scoring; version comparison | `backend/app/pipeline/analyzer.py`, `frontend/src/` |
| **Target Users** | **Primary:** Course Instructors and TAs (evaluating student submissions). **Secondary:** Student Teams and Software Engineers (authoring and debugging SRS artifacts). | Commit `f9460ae`, `d311c5f` |
| **Proposed Stack** | **Backend:** FastAPI, Python 3.11, SQLAlchemy, SQLite, Alembic. **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Radix UI. **Analysis:** `python-docx`, `pdfplumber`, Groq Cloud API (`llama3-8b-8192`). | `requirements.txt`, `package.json`, `docker-compose.yml` |
| **Timeline** | 16-Week University Semester (Phases 0 through 7) | Academic semester calendar; Phase 0–7 git tags |
| **Team Size** | 4 Student Engineers (SRS/NLP, UML, Traceability/Backend, Frontend/UI) | Repository team delegation matrix (`d311c5f:README.md`) |
| **Constraints** | Zero financial budget; student academic timeline; reliance on Groq free-tier rate limits; local SQLite concurrency boundaries. | Workspace environment (`.env`, `config.yaml`) |

### Documented Assumptions
1. **Academic Evaluation Context:** It is assumed that the template's blank administrative headers (`[Instructor Name]`, `[Student Name]`, `Group No: [ ]`) represent the official submission for GIKI CS325 (Fall Semester, 5th Semester BS CS).
2. **Operational Infrastructure:** The target deployment environment is assumed to be single-server/local workstation testing via Docker Compose or Uvicorn/Vite development servers, as no cloud infrastructure budget is allocated.
3. **Document Conformity:** It is assumed that student input documents conform nominally to IEEE-830 / IEEE 29148 formatting conventions with standard identifiers (`FR-xxx`, `NFR-xxx`) and "shall" phrasing, as assumed by the regex parsing engine.
4. **LLM Availability:** It is assumed that Groq Cloud maintains continuous availability of the `llama3-8b-8192` endpoint and that API keys remain active within free-tier quotas.

---

## 1. Executive Summary

SRS Reviewer is an automated quality assurance web application engineered to ingest Software Requirements Specifications (in DOCX/PDF formats) and PlantUML architectural models, parse requirement syntax, flag architectural and semantic defects, and suggest testable requirement rewrites through an agentic feedback loop. Developed as a 5th-semester Software Engineering course project at GIK Institute with a dual focus on academic grading and developer tooling, the system replaces slow, subjective manual reviews with deterministic rule checks and LLM-powered verification. While the core prototype successfully demonstrates high baseline rule precision (0.98 F1-score on benchmark data) and robust UI integration, critical engineering risks remain around external LLM API rate limits, brittle regex-based diagram parsing, and SQLite database concurrency locks under multi-user loads. 

**Verdict: Feasible with Changes.**  
The project is conceptually sound and functional as a single-user prototype; however, progressing to production or classroom-wide cohort deployment requires targeted architectural revisions: migrating from SQLite to PostgreSQL, substituting naive regex PlantUML parsing with formal grammar validation, replacing lexical Jaccard traceability with local semantic embeddings, and implementing rate-limited batch queuing for LLM calls.

---

## 2. Problem and Objectives

### 2.1 Problem Definition
In academic software engineering courses and industrial requirements engineering alike, reviewing Software Requirements Specifications (SRS) and UML system models is executed manually. This manual process suffers from three systemic failures:
1. **Subjectivity and Inconsistency:** Human evaluators inconsistently detect non-atomic statements, ambiguous terminology (e.g., "fast", "user-friendly"), and unquantified Non-Functional Requirements (NFRs).
2. **Undetected Cross-Artifact Drift:** Verifying traceability between natural language requirements, use cases, sequence messages, and class diagrams by hand is intractable for large specifications, allowing disconnected actors, undefined classes, and orphan requirements to slip into implementation.
3. **Delayed Feedback Loops:** Students and developers receive defect reports days or weeks after drafting, lacking immediate, actionable rewrites to correct ambiguous clauses during the design stage.

### 2.2 Project Objectives and Measurable Success Criteria

| Objective ID | Objective Description | Metric / Target | Measurement Method |
| :--- | :--- | :--- | :--- |
| **OBJ-01** | **Automated Parsing & Ingestion** | Extract $\ge 95\%$ of requirements from IEEE-style DOCX/PDF files and entities from PlantUML diagrams. | Automated parse test against structured benchmark files. |
| **OBJ-02** | **Deterministic Defect Detection** | Achieve $\ge 90\%$ Precision and $\ge 85\%$ Recall on core structural and lexicon defects (FR-401, FR-402, FR-409, FR-410, FR-411). | Empirical benchmark execution against `backend/eval/dataset.json`. |
| **OBJ-03** | **Multi-Tier Traceability Linkage** | Automatically infer transitive trace links (Requirement $\rightarrow$ Use Case $\rightarrow$ Sequence $\rightarrow$ Class) with user override capabilities. | Matrix generation with CSV export and user review UI. |
| **OBJ-04** | **Agentic Rewrite Generation** | Proactively rewrite defective requirements using an LLM, validating rewrites against deterministic rules within 3 iterations. | Loop convergence rate and validation pass flag (`rewrite_passed == True`). |
| **OBJ-05** | **Execution Throughput** | Complete complete multi-stage analysis pipeline in $< 15$ seconds for standard specifications (10–25 pages, $\le 50$ requirements). | End-to-end API latency logging (`LLMLog` and pipeline timer). |
| **OBJ-06** | **Normalized Grading Rubric** | Compute objective quality scores (40% Requirements, 30% UML, 30% Traceability) normalized against element density. | Defect penalty formula verification in `backend/config.yaml`. |

---

## 3. Technical Feasibility

### 3.1 Proposed Architecture and Stack Evaluation

The platform utilizes a decoupled client-server architecture containerized via Docker:
- **Frontend:** Single Page Application (SPA) built with React 18, TypeScript, Vite, Tailwind CSS, Radix UI primitives, and TanStack React Query.
- **Backend API:** Python 3.11 with FastAPI (v0.111.0), SQLAlchemy ORM (v2.0.30), Alembic migrations (v1.13.1), and Uvicorn.
- **Database:** SQLite 3 file-based storage (`srs_reviewer.db`).
- **External AI Service:** Groq Cloud API running `llama3-8b-8192` with structured JSON mode.
- **Parsing Libraries:** `python-docx` (v1.1.2), `pdfplumber` (v0.11.0), and regex-based PlantUML extractors.

```
+---------------------------------------------------------------------------------+
|                                Frontend (React 18 + TS)                         |
|      [Upload Forms]  |  [Findings Table]  |  [Trace Matrix]  |  [Score Cards]   |
+---------------------------------------------------------------------------------+
                                       | HTTP / REST (JWT Auth)
                                       v
+---------------------------------------------------------------------------------+
|                               Backend (FastAPI)                                 |
|                                                                                 |
|  +---------------------------------------------------------------------------+  |
|  |                             Pipeline Engine                               |  |
|  |  +------------------+     +------------------+     +-------------------+  |  |
|  |  |  Document Parser | --> |  Deterministic   | --> | Traceability Link |  |  |
|  |  | (docx/pdf/puml)  |     |  Rule Engine     |     | (Jaccard Overlap) |  |  |
|  |  +------------------+     +------------------+     +-------------------+  |  |
|  |                                     |                         |           |  |
|  |                                     v                         |           |  |
|  |                           +-------------------+               |           |  |
|  |                           |  Agentic Repair   |               |           |  |
|  |                           | (Groq / Llama-3)  |               |           |  |
|  |                           +-------------------+               |           |  |
|  |                                     |                         |           |  |
|  |                                     +------------+------------+           |  |
|  |                                                  v                        |  |
|  |                                        +-------------------+              |  |
|  |                                        |  Scoring Engine   |              |  |
|  |                                        +-------------------+              |  |
|  +---------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------+
           |                                                      |
           v                                                      v
  [SQLite Database]                                      [Groq Cloud API]
 (Metadata, Findings,                                   (JSON Completions,
  Trace Links, Scores)                                    Rate-Limited)
```

### 3.2 Component Suitability, Unproven Elements, and Technical Risks

| Pipeline Component | Underlying Technology | Technical Assessment | Risk Rating | Identified Deficiencies & Failure Modes |
| :--- | :--- | :--- | :---: | :--- |
| **Requirements Parsing** | `python-docx` & `pdfplumber` | **Adequate for standard IEEE, brittle for generic formats.** | **Medium** | Relies entirely on strict regex heading detection (`_is_section_heading`) and the explicit presence of `"shall"` or ID prefixes (`FR-`, `NFR-`). Fails on narrative requirements, tables without ID columns, or multi-column PDFs. |
| **UML Diagram Parsing** | Custom Regex heuristics (`uml/parser.py`) | **High Fragility / Unproven for complex syntax.** | **High** | Regex cannot parse full PlantUML Backus-Naur Form (BNF). Multiline associations, nested namespaces, inline notes, packages, skinparam blocks, and complex sequence loops fail or generate spurious errors. |
| **Traceability Engine** | Set Jaccard Overlap ($\text{threshold} = 0.3$) | **Rudimentary Lexical Matching.** | **Medium** | Strictly lexical. Fails when distinct vocabularies express identical concepts (e.g., "Authenticate User" vs "Verify Credentials"). Produces false positives on generic domain nouns. |
| **LLM Checks & Repair Loop** | Groq Cloud API (`llama3-8b-8192`) | **Functional but vulnerable to rate limits and network variance.** | **High** | Groq free tier enforces strict request caps (30 RPM). The agentic loop executes up to 3 LLM calls per defective requirement (max 50 calls/project). Multi-requirement files trigger HTTP 429 timeouts. |
| **Data Persistence** | SQLite 3 (`srs_reviewer.db`) | **Insufficient for concurrent workloads.** | **High** | SQLite enforces database-level write locks. When multiple asynchronous analysis pipelines execute concurrently, write collisions trigger `sqlite3.OperationalError: database is locked`. |

### 3.3 Scalability Boundaries
1. **Concurrent Processing:** Background tasks running via FastAPI share a single file-backed SQLite database. The system cannot safely handle $> 2$ concurrent pipeline executions without database lock contention.
2. **File Storage:** Uploads are stored directly in local directories (`uploads/{project_id}/`), prohibiting stateless horizontal scaling across clustered container instances.
3. **Token & Rate Ceilings:** Groq's 30 RPM limit limits platform throughput to approximately 1 complex document analysis per minute when the agentic repair loop is active.

---

## 4. Resource Feasibility

### 4.1 Team Competencies vs. Required Capabilities
The project was executed by a team of 4 undergraduate software engineering students (5th Semester BS CS).

| Domain | Assigned Role | Required Skillset | Observed Team Skill Level | Gap Analysis & Remediation |
| :--- | :--- | :--- | :---: | :--- |
| **SRS Parsing & Rule Checks** | SRS & NLP Engineer | Python, Regex, AST parsing, NLP tokenization | **Medium** | Implemented regex rules cleanly (achieved 0.98 F1 on baseline), but lacked advanced NLP / parsing techniques for unstructured syntax. |
| **UML Grammar & Validation** | UML Modeling Engineer | Formal language grammars, PlantUML AST, Graph Theory | **Low–Medium** | Relied on naive regex matching instead of compiling PlantUML with an official parser or grammar engine. |
| **Traceability & Backend API** | Traceability & Backend Engineer | FastAPI, SQLAlchemy, Async programming, Information Retrieval | **Medium–High** | Clean REST design, migration management (Alembic), and pipeline orchestration. Lexical Jaccard algorithm requires replacement with vector embeddings. |
| **User Interface & Visualization** | Frontend / UI Engineer | React 18, TypeScript, Tailwind, State Management | **High** | High-quality component architecture, clean dashboard layouts, and interactive finding/traceability inspection views. |

### 4.2 Hardware, Infrastructure, and Tooling Requirements
- **Development Workstations:** Standard developer laptops (x86_64, $\ge 8$ GB RAM, Windows 11 / Linux).
- **Runtime Environment:** Docker Engine 24.0+ and Docker Compose v2.0+ (verified via `docker-compose.yml`).
- **Testing Tools:** `pytest` (v8.2+) test suite configured in `backend/tests/`.

### 4.3 Datasets and Benchmark Availability
- **Evaluation Dataset:** `backend/eval/dataset.json` contains 30 curated test requirement statements mapping to specific deterministic error rules (`FR-401`, `FR-402`, `FR-409`, `FR-410`, `FR-411`).
- **Resource Limitation:** The current dataset is synthetic and small ($N = 30$). The team lacks an expansive, publicly vetted academic SRS corpus to benchmark real-world variance.

### 4.4 Third-Party APIs and Software Licensing
All libraries and external services are verified to exist, are actively maintained, and carry permissive licensing suitable for academic and commercial applications:
- **FastAPI / Starlette:** MIT License (free for commercial/academic use).
- **SQLAlchemy / Alembic:** MIT License.
- **python-docx / pdfplumber:** MIT License.
- **React / Vite / Tailwind CSS / Radix UI:** MIT License.
- **Groq Cloud API:** Proprietary cloud service; operates under a free developer tier with usage quotas.
- **Llama 3 Model:** Governed by the Meta Llama 3 Community License Agreement (permissive commercial use permitted for applications under 700M monthly active users).

---

## 5. Time Feasibility

### 5.1 Work Breakdown Structure (WBS) and Phase Effort Allocation
The project scope is partitioned across eight structured phases across the 16-week academic semester:

```
Week:     1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16
Phase 0: [===]
Phase 1:     [===]
Phase 2:         [===]
Phase 3:             [===]
Phase 4:                 [===]
Phase 5:                     [===]
Phase 6:                         [===]
Phase 7:                             [===]
```

| Phase | Milestone Description | Primary Deliverables | Estimated Effort | Actual Git Status |
| :--- | :--- | :--- | :---: | :---: |
| **Phase 0** | Project Setup & Baseline Scaffolding | Docker setup, FastAPI/React skeleton, repository guidelines | 25 person-hrs | Completed (`0041868`) |
| **Phase 1** | Pipeline Core & Data Modeling | SQLAlchemy models, initial analyzer, bug fixes | 35 person-hrs | Completed (`ed10316`) |
| **Phase 2** | Security & Input Validation | JWT authentication, RBAC, file upload sanitization | 30 person-hrs | Completed (`9528cfb`) |
| **Phase 3** | Ingestion & Deterministic Rules | DOCX/PDF parsers, IEEE rule checks (FR-401 to FR-411) | 40 person-hrs | Completed (`22fe172`) |
| **Phase 4** | UML Modeling & Traceability | PlantUML parser, Jaccard trace linker, matrix CSV export | 45 person-hrs | Completed (`e0216fe`) |
| **Phase 5** | Scoring Engine & Versioning | Normalized quality score, version diffing, snapshotting | 30 person-hrs | Completed (`70e60c3`) |
| **Phase 6** | Agentic LLM Repair Loop | Groq provider integration, prompt caching, iterative rewrites | 40 person-hrs | Completed (`dce3420`) |
| **Phase 7** | Evaluation, Reporting & Final UI | Precision/Recall benchmark, PDF report printing, docs | 25 person-hrs | Completed (`81c1aa2`) |
| **Total** | **Full Project Lifecycle** | **Fully integrated Tier-1 Prototype** | **270 person-hrs** | **Delivered** |

### 5.2 Schedule Feasibility Assessment
With a 4-person team working over 16 weeks, 270 person-hours equates to approximately **4.2 hours per team member per week**. This is well within standard undergraduate course credit expectations (3 credit hours = ~6–9 study hours/week). 

**Finding:** The development schedule was highly feasible and has been validated by actual project delivery. However, remaining technical debt (e.g., rewriting the UML parser as a formal AST or migrating to PostgreSQL) would require an additional estimated 40–50 person-hours, which cannot fit within the current semester without formal scope de-scoping.

---

## 6. Cost Feasibility

### 6.1 Financial Budget Overview
As an academic course project, the direct financial budget is **PKR 0 (N/A)**. The analysis below evaluates both the current zero-cost footprint and the projected operational costs if transitioned into institutional or commercial SaaS hosting.

| Cost Category | Item Description | Current Academic Cost (PKR) | Commercial / Cloud Scaling Cost (USD / PKR) | Basis of Estimate |
| :--- | :--- | :---: | :---: | :--- |
| **Development** | Student Engineering Labor (4 members $\times$ 270 hrs) | PKR 0 | N/A (Internal Course Work) | Academic coursework. |
| **Infrastructure** | Local Workstations & Docker Compose | PKR 0 | Cloud VPS (4 vCPU, 8GB RAM): ~$24/mo (PKR 6,700/mo) | DigitalOcean / Hetzner cloud compute pricing. |
| **Database** | SQLite File Database | PKR 0 | Managed PostgreSQL: ~$15/mo (PKR 4,200/mo) | Managed cloud database pricing. |
| **LLM Services** | Groq Cloud API (`llama3-8b-8192`) | PKR 0 | Free tier currently; Paid Groq: ~$0.05 / 100k tokens | Current usage fits entirely inside Groq free tier. |
| **Licensing** | Open-source dependencies (FastAPI, React, etc.) | PKR 0 | PKR 0 | Permissive MIT / Apache 2.0 open-source licenses. |
| **Domain & SSL** | Localhost execution / University intranet | PKR 0 | Custom Domain + Cloudflare SSL: ~$12/yr (PKR 3,350/yr) | Standard TLD registrar pricing. |
| **Total** | — | **PKR 0** | **~PKR 11,000 / month** | Academic zero-cost mode is 100% sustainable. |

### 6.2 Economic Justification
The project delivers exceptional return on investment (ROI): for zero monetary outlay, it replaces dozens of instructor grading hours per semester and provides immediate, automated quality validation to student cohorts. If commercialized, operating costs remain under PKR 0.20 per analyzed document, making it highly economically viable.

---

## 7. Operational and Legal Feasibility

### 7.1 Operational Feasibility & User Acceptance
1. **Deployment Simplicity:** The inclusion of `docker-compose.yml`, `run_backend.ps1`, and `run_frontend.ps1` enables reproducible one-command setup for instructors and evaluators.
2. **User Workflow Impact:** The system integrates naturally into academic grading pipelines: students upload documents, the pipeline analyzes them in background tasks, and instructors review pre-scored findings rather than reading every line manually.
3. **Maintenance Overhead:** High reliance on regular expressions creates ongoing maintenance overhead; whenever students submit non-standard document formats, regex heuristics must be patched.

### 7.2 Data Privacy, Compliance, and Intellectual Property
1. **PII and Data Scrubbing:** The backend implements an automated text redactor (`backend/app/pipeline/redactor.py`) that scrubs email addresses, phone numbers, and 8+ digit student IDs before dispatching prompts to Groq. 
2. **Confidentiality Vulnerability:** While simple PII patterns are masked, proprietary project requirements, novel architecture diagrams, and institutional course data are transmitted in plaintext to an external third-party API endpoint (Groq Cloud, US servers). In an enterprise or defense environment, this constitutes unauthorized data leakage under GDPR / local data protection frameworks.
3. **Intellectual Property Ownership:** Code developed under undergraduate coursework at GIK Institute remains the intellectual property of the student team under institutional academic guidelines, with no proprietary or restrictive licensing conflicts.

---

## 8. Risk Analysis

The following risk matrix evaluates technical, operational, and external risks based on empirical inspection of the codebase:

| Risk ID | Risk Description | Likelihood | Impact | Severity | Mitigation Strategy |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **R1** | **Groq Cloud API Rate Limiting (429 Errors)**<br>Batch submissions by multiple students exhaust Groq's 30 RPM limit, causing LLM checks and repair loops to fail. | **High** | **High** | **CRITICAL** | Implement request batching, exponential backoff, persistent DB caching of prompt hashes (already partially present), and configure an automatic fallback to a local LLM (e.g., Ollama running `llama3:8b`). |
| **R2** | **SQLite Database Locking Under Concurrency**<br>Simultaneous write requests from background analysis jobs cause `sqlite3.OperationalError: database is locked`. | **High** | **High** | **CRITICAL** | Migrate persistence layer from SQLite to PostgreSQL; configure connection pooling via SQLAlchemy; offload analysis tasks to Celery / Redis. |
| **R3** | **PlantUML Heuristic Regex Parsing Breakdown**<br>Complex real-world diagrams (multiline associations, packages, inline notes) fail regex extraction, yielding false defect findings. | **High** | **Medium** | **HIGH** | Replace custom regex with an official PlantUML compiler integration via PlantUML Server/JAR, or adopt a formal PEG/LALR grammar parser. |
| **R4** | **Inaccurate Traceability from Lexical Jaccard Overlap**<br>Semantically equivalent terms (e.g., "Authenticate" vs "Login") yield zero lexical overlap, generating excessive unlinked defect findings. | **High** | **Medium** | **HIGH** | Upgrade the traceability engine from Jaccard set overlap to semantic cosine similarity using a lightweight local embedding model (e.g., `sentence-transformers/all-MiniLM-L6-v2`). |
| **R5** | **Data Leakage to External Cloud Endpoints**<br>Sending full requirement specifications to Groq Cloud risks leaking institutional or proprietary student IP. | **Medium** | **High** | **HIGH** | Expand the regex redactor with Named Entity Recognition (spaCy NER) to mask project-specific nouns, or enable a strictly local execution mode (`mock` or `ollama`). |
| **R6** | **Brittleness to Non-Conforming SRS Formats**<br>Documents omitting standard IEEE numbered sections or "shall" statements bypass the parser completely. | **Medium** | **Medium** | **MEDIUM** | Implement a pre-parsing diagnostic warning students if no numbered sections or modal verbs are found; expand modal detection to include "must", "should", and "will". |
| **R7** | **LLM Repair Hallucinations & Infinite Loops**<br>LLM rewrites generate new syntactical defects or alter original requirement intent. | **Medium** | **Medium** | **MEDIUM** | Strict deterministic check re-validation after each rewrite (already implemented up to 3 attempts); enforce an immutable maximum call cap per project (`max_llm_calls_per_project: 50`). |

---

## 9. Alternatives Considered

To address the principal weaknesses identified in the technical and operational assessments, two viable alternative architectures are evaluated against the current implementation:

| Evaluation Dimension | Current Plan: Hybrid Regex + Cloud Groq LLM | Alternative A: Fully Local Deterministic & SBERT Pipeline (No Cloud LLM) | Alternative B: Shift-Left Developer CLI & IDE Plugin (Pre-Submission Linter) |
| :--- | :--- | :--- | :--- |
| **Architecture** | FastAPI + React + Groq Cloud (`llama3-8b`) | FastAPI + React + spaCy NLP + Local `all-MiniLM-L6-v2` | Python CLI / VS Code Extension parsing local Markdown & PlantUML |
| **External Dependencies** | High (Internet connection & Groq API availability required) | **None** (100% self-contained and offline) | **None** (Runs entirely on client developer machines) |
| **Rate Limit Vulnerability** | **Severe** (30 requests/minute ceiling) | **Zero** (Local inference with no API rate throttling) | **Zero** (Distributed client-side execution) |
| **Traceability Mechanism** | Brittle lexical Jaccard set overlap (0.3 threshold) | **Semantic Vector Embeddings** (Cosine similarity $\ge 0.65$) | Static regex & Markdown cross-reference links |
| **Repair Capability** | Automated LLM-generated rewrites with verification | Rule-based template fill-in recommendations | Real-time IDE diagnostics and lint warnings |
| **Data Privacy** | Moderate (Regex PII scrubbing; full text sent to cloud) | **Maximum** (Zero external data transmission) | **Maximum** (Files never leave student workstation) |
| **Implementation Effort** | Already implemented (270 person-hrs) | Low refactor (~20 person-hours to integrate SBERT) | Medium (~40 person-hours to build CLI/extension) |
| **Comparative Verdict** | **High maintenance; fragile at scale.** | **Recommended Near-Term Evolution.** | **Recommended Future Extension.** |

### Analysis of Alternatives
- **Alternative A (Local SBERT + Deterministic NLP):** Represents the highest-value, lowest-risk modification. By stripping the external Groq dependency and replacing lexical Jaccard matching with local `sentence-transformers`, all API rate limiting, network latency, and confidentiality risks are eliminated immediately while dramatically improving traceability recall.
- **Alternative B (Shift-Left Pre-Submission Linter):** Moves defect detection directly into the authoring environment (VS Code). Rather than uploading whole documents to a server post-facto, students receive instantaneous linting warnings as they type. This eliminates server compute overhead entirely.

---

## 10. Recommendation and Next Steps

### 10.1 Definitive Recommendation: REVISE (Feasible with Changes)

The SRS Reviewer project has demonstrated strong conceptual value, solid foundational engineering, and impressive initial accuracy on formatted benchmark documents. However, advancing this system from an isolated academic demonstration to an operational grading platform or production developer tool requires addressing the structural vulnerabilities highlighted in this report. Proceeding under the current architecture without modifications will inevitably lead to database lock failures under multi-user cohort submissions and API throttling during evaluation deadlines.

### 10.2 Prioritized Action Plan

```
+-----------------------------------------------------------------------------------+
|                            PRIORITIZED ROADMAP                                   |
|                                                                                   |
|  [P0: Immediate / Critical]                                                       |
|  - Migrate DB from SQLite to PostgreSQL (Dockerized)                              |
|  - Implement Celery/Redis queue for background analysis jobs                     |
|  - Add exponential backoff & rate-limit throttling for Groq API calls             |
|                                                                                   |
|  [P1: Near-Term Enhancements]                                                     |
|  - Replace Jaccard overlap with local Sentence-Transformers (all-MiniLM-L6-v2)    |
|  - Upgrade PlantUML parser to use official PlantUML compiler/server AST          |
|  - Expand modal verb detection (support "must", "should", "will", agile stories) |
|                                                                                   |
|  [P2: Long-Term Scaling]                                                          |
|  - Support local quantized LLMs (Ollama / Llama-3-8B-GGUF) for 100% offline mode  |
|  - Develop lightweight VS Code extension for pre-submission linting               |
|  - Integrate Named Entity Recognition (NER) for enterprise-grade privacy masking  |
+-----------------------------------------------------------------------------------+
```

1. **Immediate P0 (Stability & Concurrency - Week 1–2):**
   - Replace SQLite with PostgreSQL in `docker-compose.yml` to prevent concurrency crashes.
   - Decouple background analysis from synchronous FastAPI worker threads using a lightweight Redis/Celery queue.
   - Wrap Groq API calls in strict rate-limiting middleware with exponential backoff and persistent database caching to handle HTTP 429 errors gracefully.

2. **Near-Term P1 (Quality & Precision - Week 3–4):**
   - Replace lexical Jaccard overlap in `traceability_checks.py` with local vector embeddings (`sentence-transformers/all-MiniLM-L6-v2`) to capture semantic equivalence between requirements and architecture diagrams.
   - Replace regex parsing in `uml/parser.py` with official PlantUML AST compilation via the PlantUML Web Server Docker container.
   - Broaden requirements classification in `srs/parser.py` to support agile user stories and ISO/IEC/IEEE 29148 modal verbs.

3. **Future P2 (Privacy & Tooling - Post-Semester):**
   - Provide an optional fully offline mode utilizing Ollama running locally quantized Llama-3 models.
   - Package deterministic checking rules into a standalone CLI tool for CI/CD pre-commit hooks.

### 10.3 Suggested MVP Scope for Production Deployment

| Module / Feature | In MVP Scope (Core) | Deferred to Post-MVP (Phase 2) |
| :--- | :---: | :---: |
| **DOCX and PDF Requirements Extraction** | **Yes** (Standard IEEE structures) | Arbitrary multi-column layout extraction |
| **Deterministic Rule Checks (FR-401 to FR-411)** | **Yes** (100% complete) | Custom rule creation UI |
| **PlantUML Class & Use Case Parsing** | **Yes** (Standard syntax) | Complex nested state & activity diagrams |
| **Traceability Link Suggestions** | **Yes** (Hybrid SBERT + Lexical) | Automated bidirectional code traceability |
| **Normalized Scoring Engine & Rubric** | **Yes** (100% complete) | Custom rubric weight editor |
| **Agentic LLM Repair Loop** | **Yes** (Capped at 3 retries, max 25 calls) | Unbounded multi-turn dialogue refactoring |
| **Persistent Multi-User Database** | **Yes** (PostgreSQL required) | Multi-tenant enterprise SSO / SAML auth |
| **Cloud LLM Redaction & Caching** | **Yes** (SHA-256 DB cache & Regex PII) | Deep contextual Named Entity Recognition |
