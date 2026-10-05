import re
with open('backend/app/routers/projects.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add config import
text = text.replace('from ..core.database import get_db', 'from ..core.database import get_db\nfrom ..core.config import get_settings')

# Remove hardcoded UPLOAD_DIR
text = re.sub(r'UPLOAD_DIR =.*?\n', '', text)

# Rewrite upload_srs and upload_uml
replacement = '''@router.post("/{project_id}/upload-srs")
async def upload_srs(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    settings = get_settings()
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
        
    ext = "txt"
    if content.startswith(b"PK"):
        ext = "docx"
    elif content.startswith(b"%PDF"):
        ext = "pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid file type. Only DOCX (zip) and PDF allowed.")
        
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)
    
    with open(file_path, "wb") as f:
        f.write(content)
        
    artifact = db.query(Artifact).filter(Artifact.project_id == project.id, Artifact.artifact_type == "srs").first()
    if artifact:
        if os.path.exists(artifact.file_path):
            try: os.remove(artifact.file_path)
            except: pass
        artifact.file_format = ext
        artifact.file_path = file_path
        artifact.original_filename = file.filename
    else:
        artifact = Artifact(
            project_id=project.id,
            artifact_type="srs",
            file_format=ext,
            file_path=file_path,
            original_filename=file.filename
        )
        db.add(artifact)
    db.commit()
    return {"message": "SRS uploaded"}

@router.post("/{project_id}/upload-uml")
async def upload_uml(project_id: int, uml_type: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    settings = get_settings()
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if uml_type not in ["usecase", "class", "sequence"]:
        raise HTTPException(status_code=400, detail="Invalid UML type")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
        
    client_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if client_ext not in ["puml", "txt", "plantuml"]:
        raise HTTPException(status_code=400, detail="Invalid UML extension. Only .puml, .txt, .plantuml allowed.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4()}.{client_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    atype = f"uml_{uml_type}"
    artifact = db.query(Artifact).filter(Artifact.project_id == project.id, Artifact.artifact_type == atype).first()
    if artifact:
        if os.path.exists(artifact.file_path):
            try: os.remove(artifact.file_path)
            except: pass
        artifact.file_format = client_ext
        artifact.file_path = file_path
        artifact.original_filename = file.filename
    else:
        artifact = Artifact(
            project_id=project.id,
            artifact_type=atype,
            file_format=client_ext,
            file_path=file_path,
            original_filename=file.filename
        )
        db.add(artifact)
    db.commit()
    return {"message": f"{uml_type} UML uploaded"}'''

# Replace from @router.post("/{project_id}/upload-srs") down to before analyze_project
pattern = r'@router\.post\("/\{project_id\}/upload-srs"\).*?return \{"message": f"\{uml_type\} UML uploaded"\}'
text = re.sub(pattern, replacement, text, flags=re.DOTALL)

with open('backend/app/routers/projects.py', 'w', encoding='utf-8') as f:
    f.write(text)
