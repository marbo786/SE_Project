import os

with open('backend/app/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

startup_code = '''
@app.on_event("startup")
def startup_event():
    from .core.database import SessionLocal
    from .models.project import Project
    from .models.finding import Finding
    db = SessionLocal()
    try:
        stuck_projects = db.query(Project).filter(Project.status == "analyzing").all()
        for p in stuck_projects:
            p.status = "error"
            # Add an error finding so user knows what happened
            f = Finding(
                project_id=p.id,
                rule_id="SYS-ERR",
                severity="critical",
                explanation="Analysis was interrupted (server restarted). Please try re-analyzing.",
                finding_type="system"
            )
            db.add(f)
        db.commit()
    finally:
        db.close()

# Include routers'''

text = text.replace('# Include routers', startup_code)

with open('backend/app/main.py', 'w', encoding='utf-8') as f:
    f.write(text)
