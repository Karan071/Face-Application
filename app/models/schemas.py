from pydantic import BaseModel

class UserBase(BaseModel):
    name: str
    age: int
    gender: str

class UserCreate(UserBase):
    photo: bytes

class UserResponse(UserBase):
    createdAt: str
    updatedAt: str
