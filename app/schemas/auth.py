from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

class UserResponse(UserBase):
    id: int

    model_config = {"from_attributes": True}

class VerifyAccountSubmit(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{4}$")

class ResendVerificationSubmit(BaseModel):
    email: EmailStr

class PasswordResetSubmit(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str = Field(min_length=8, max_length=128)