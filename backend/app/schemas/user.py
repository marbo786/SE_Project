from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower()

class UserCreate(UserLogin):
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=128)
    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        return value

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    email_verified: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class RecoveryRequest(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=128)

class VerifyEmail(BaseModel):
    token: str = Field(min_length=32, max_length=256)
