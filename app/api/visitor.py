from fastapi import APIRouter, UploadFile, HTTPException, Form
from app.services.deepface import extract_face_embedding
from app.services.milvus import create_milvus_collection, save_to_milvus
from app.core.db import db
from app.models.schemas import UserCreate, UserResponse

router = APIRouter()

@router.post("/register-visitor/")
async def register_visitor(user: UserCreate):
    try:
        embedding = extract_face_embedding(user.photo)
        await db.visitor.create(data={"name": user.name, "age": user.age, "gender": user.gender})
        save_to_milvus("visitor_embeddings", user.name, embedding)
        return {"message": "Visitor registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")
