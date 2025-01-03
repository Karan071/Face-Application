from pydantic import BaseModel, EmailStr

class UserRegistrationModel(BaseModel):
    username: str
    email: EmailStr
    fullName: str  # Exactly matching Prisma schema
    password: str
    role: str = "user"

    class Config:
        from_attributes = True
