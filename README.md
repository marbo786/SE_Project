# SRS Reviewer

SRS Reviewer is an AI-powered SaaS tool for Software Engineers and Product Managers. It acts like **Grammarly for Software Engineering**, instantly analyzing your Software Requirements Specifications (SRS) and UML diagrams for defects, ambiguities, conflicting requirements, and missing traceability.

## Features

- **Automated Requirement Checks:** Instantly flags ambiguous phrasing, non-atomic requirements, missing identifiers, and missing NFR metrics.
- **LLM-Powered Rewrites:** Uses advanced AI (Groq/LLaMA) to not only find issues but proactively suggest perfectly rewritten, testable requirements.
- **Architecture Validation:** Upload PlantUML diagrams (Use Case, Class, Sequence) and the system cross-checks them to ensure your text and architecture align.
- **Traceability Matrix:** Automatically builds and tracks relationships between your functional requirements, use cases, and classes to ensure no dead-ends.
- **Version History & Diffing:** Re-upload a document and immediately see which findings you resolved, which persisted, and if you introduced any new bugs.
- **PDF Export:** Clean, one-click exports of your analysis reports.

## Quality Scoring Formula

The system calculates normalized scores for Requirements, UML, and Traceability based on defect density (penalties per element) to ensure long documents aren't disproportionately penalized.

- **Element Count**: Number of requirements, UML elements, or trace links.
- **Base Penalty**: Sum of penalties for findings (Critical = 15, Major = 5, Minor = 2).
- **Raw Category Score** = `max(0, 100 - (Base Penalty / Element Count) * 10)`

The final overall score is a weighted average configured via `config.yaml` (e.g., Requirements 40%, UML 30%, Traceability 30%).

## Tech Stack

- **Frontend:** React, Vite, Tailwind CSS, TypeScript
- **Backend:** FastAPI, Python, SQLAlchemy, SQLite
- **AI / LLM:** Groq API (llama3) for high-speed AI analysis.

## Getting Started

### 1. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables:
   Create a `.env` file in the `backend/` directory:
   ```env
   SECRET_KEY=your_secret_key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   GROQ_API_KEY=your_groq_api_key_here
   LLM_PROVIDER=groq
   DATABASE_URL=sqlite:///./srs_reviewer.db
   ```
4. Run the server:
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

### 2. Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

## Usage

1. Open `http://localhost:5173` in your browser.
2. Register for a new account.
3. Click **"Analyze New SRS"** from your Dashboard.
4. Upload your SRS (`.docx` or `.pdf`) and any optional PlantUML diagrams (`.txt`, `.puml`).
5. Review the comprehensive quality report, grab the AI rewrite suggestions, and export your PDF!

