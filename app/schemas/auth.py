from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    username: str
    email: EmailStr
    is_verified: bool = True

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int

    model_config = {"from_attributes": True}