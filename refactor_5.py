import os
import re

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

# --- 6. PIPELINE ---
analyzer_content = read_file('backend/app/pipeline/analyzer.py')

# Fix imports in analyzer.py
analyzer_content = analyzer_content.replace(
    "from ..models.submission import Submission",
    "from ..models.project import Project"
)

# Rename function arg
analyzer_content = analyzer_content.replace(
    "def run_analysis_pipeline(submission_id: int):",
    "def run_analysis_pipeline(project_id: int):"
)
analyzer_content = analyzer_content.replace("submission_id", "project_id")

# Replace Submission with Project
analyzer_content = analyzer_content.replace("db.query(Submission)", "db.query(Project)")
analyzer_content = analyzer_content.replace("Submission.id", "Project.id")
analyzer_content = analyzer_content.replace("submission = db.query", "project = db.query")
analyzer_content = analyzer_content.replace("if submission:", "if project:")
analyzer_content = analyzer_content.replace("submission.status", "project.status")

write_file('backend/app/pipeline/analyzer.py', analyzer_content)

# llm_checks.py
llm_content = read_file('backend/app/pipeline/checks/llm_checks.py')
llm_content = llm_content.replace("submission_id", "project_id")
write_file('backend/app/pipeline/checks/llm_checks.py', llm_content)

# engine.py
engine_content = read_file('backend/app/llm/engine.py')
engine_content = engine_content.replace("submission_id", "project_id")
write_file('backend/app/llm/engine.py', engine_content)

# main.py
main_content = read_file('backend/app/main.py')
main_content = main_content.replace("from .models import user, assignment, submission, artifact, finding, traceability as trace_model, llm_log, score", "from .models import user, project, artifact, finding, traceability as trace_model, llm_log, score")
main_content = main_content.replace("from .routers import auth, assignments, submissions, findings, traceability, dashboard", "from .routers import auth, projects, findings, traceability, dashboard")
main_content = main_content.replace("app.include_router(assignments.router)", "")
main_content = main_content.replace("app.include_router(submissions.router)", "app.include_router(projects.router)")
write_file('backend/app/main.py', main_content)
