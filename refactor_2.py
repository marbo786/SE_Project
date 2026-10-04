import os

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

def delete_file(path):
    if os.path.exists(path):
        os.remove(path)

# --- 3. SCHEMAS ---
write_file('backend/app/schemas/user.py', """
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
""")

write_file('backend/app/schemas/project.py', """
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    version: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
""")

write_file('backend/app/schemas/finding.py', """
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FindingOut(BaseModel):
    id: int
    rule_id: str
    severity: str
    quoted_text: Optional[str]
    explanation: str
    artifact_type: Optional[str]
    requirement_id: Optional[str]
    finding_type: str
    rewrite_suggestion: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
""")

delete_file('backend/app/schemas/assignment.py')
delete_file('backend/app/schemas/submission.py')

# --- 4. ROUTERS ---
write_file('backend/app/routers/auth.py', """
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import verify_password, get_password_hash, create_access_token
from ..core.deps import get_current_user
from ..models.user import User
from ..schemas.user import UserCreate, UserLogin, Token, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = get_password_hash(user_in.password)
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.id})
    return {"access_token": access_token, "user": new_user}

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "user": user}

@router.get("/me", response_model=UserOut)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
""")
