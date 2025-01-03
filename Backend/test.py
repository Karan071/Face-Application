from fastapi import FastAPI, HTTPException, UploadFile, Form, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from prisma import Prisma
from prisma.errors import PrismaError
from pymilvus import connections, Collection
from deepface import DeepFace
from PIL import Image
import numpy as np
import os
import base64
import uvicorn
import asyncio
from datetime import datetime, timedelta
import pytz
import tempfile
import time
from fastapi_login import LoginManager
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from passlib.context import CryptContext
from jose import jwt

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

SECRET_KEY = "Karan-face-application-key"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(
    title="Face Recognition",
    description="Backend for Face Recognition App with Prisma and Milvus",
    version="1.0"
)

# Initialize LoginManager
manager = LoginManager(SECRET_KEY, token_url="/auth/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")

def hashed_password(password : str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password:str, hash_password: str) -> bool :
    return pwd_context.verify(plain_password, hash_password)

def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Prisma client
db = Prisma()


# Pydantic model for user registration
class UserRegistrationModel(BaseModel):
    username: str
    email: EmailStr
    fullName: str = Field(..., alias="fullName")
    password: str
    role: str = "user"


class User(BaseModel):
    username: str
    password: str
    email: EmailStr
    role: str

class UserLoginModel(BaseModel):
    username: str
    password: str

class EmployeeRegistrationModel(BaseModel):
    name: str = Field(...)
    age: int = Field(...)
    gender: str = Field(...)
    designation: str = Field(...)
    contactNumber: str = Field(...)
    department: str = Field(...)
    description: str = Field(...)

class VisitorRegistrationModel(BaseModel):
    name: str = Field(...)
    age: int = Field(...)
    gender: str = Field(...)
    contact: str = Field(...)
    purposeOfVisit: str = Field(...)
    description: Optional[str] = Field(None)

class RecognitionPhotoModel(BaseModel):
    photo: UploadFile

# Dependency for user authentication
@manager.user_loader
async def load_user(username: str):
    try:
        user = await db.user.find_first(where={"username": username})
        if user:
            print(f"Found user: {user}")
        else:
            print(f"User with username {username} not found.")
        return user
    except Exception as e:
        print(f"Error in user loader: {str(e)}")
        return None

    
@app.on_event("startup")
async def startup():
    max_retries = 5
    for attempt in range(max_retries):
        try:
            await db.connect()
            print("Connected to PostgreSQL database")
            break
        except PrismaError as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Failed to connect to database after {max_retries} attempts")
            print(f"Database connection attempt {attempt + 1} failed, retrying...")
            await asyncio.sleep(5)
    connect_to_milvus()
    preload_deepface_model()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()
    if connections.has_connection("default"):
        connections.remove_connection("default")

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
EMPLOYEE_COLLECTION = "employee_embeddings"
VISITOR_COLLECTION = "visitor_embeddings"

MODEL_NAME = "VGG-Face"

# Greeting API endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the face recognition app!"}

def connect_to_milvus():
    attempts = 5
    for attempt in range(attempts):
        try:
            if connections.has_connection("default"):
                connections.remove_connection("default")

            connections.connect(
                alias="default",
                host=MILVUS_HOST,
                port=MILVUS_PORT,
                timeout=60
            )
            print(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
            return True
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    raise RuntimeError("Failed to connect to Milvus after several attempts")

def preload_deepface_model():
    """
    Preload DeepFace model to resolve lazy initialization issues.
    """
    try:
        dummy_image = np.zeros((224, 224, 3), dtype=np.uint8)
        dummy_image_path = os.path.join(tempfile.gettempdir(), "dummy_image.jpg")
        Image.fromarray(dummy_image).save(dummy_image_path)
        DeepFace.represent(img_path=dummy_image_path, model_name=MODEL_NAME, enforce_detection=False)
        os.remove(dummy_image_path)
        print("DeepFace model preloaded successfully")
    except Exception as e:
        print(f"Error during DeepFace model preload: {str(e)}")

# --- Face Embedding Utilities ---
def extract_face_embedding(photo_bytes: bytes):
    """
    Extract face embedding using DeepFace with built-in detection.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(photo_bytes)
            temp_file_path = temp_file.name

        embedding = DeepFace.represent(
            img_path=temp_file_path,
            model_name=MODEL_NAME,
            enforce_detection=True
        )

        os.remove(temp_file_path)
        return embedding[0]["embedding"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting embedding: {str(e)}")

def format_datetime(dt: datetime) -> str:
    ist = pytz.timezone('Asia/Kolkata')
    dt_ist = dt.astimezone(ist)
    return dt_ist.strftime("%B %d, %Y at %I:%M %p IST")

# Milvus and Prisma Operations
def save_to_milvus(collection_name, name, embedding):
    collection = Collection(collection_name)
    data = [[name], [embedding]]
    collection.insert(data)
    collection.flush()

async def save_to_prisma(name: str, age: int, gender: str, photo_base64: str, table: str, additional_data: dict):
    if table == "employee":
        record = await db.employee.create(
            data={
                "name": name,
                "age": age,
                "gender": gender,
                "photoBase64": photo_base64,
                **additional_data
            }
        )
    elif table == "visitor":
        record = await db.visitor.create(
            data={
                "name": name,
                "age": age,
                "gender": gender,
                "photoBase64": photo_base64,
                **additional_data
            }
        )
    return {
        **record.model_dump(),
        "createdAt": format_datetime(record.createdAt),
        "updatedAt": format_datetime(record.updatedAt)
    }

def search_in_milvus(collection_name, query_embedding, threshold=0.6):
    try:
        query_embedding = np.array(query_embedding) / np.linalg.norm(query_embedding)
        collection = Collection(collection_name)
        results = collection.search(
            data=[query_embedding.tolist()],
            anns_field="embedding",
            param={"metric_type": "IP", "params": {"nprobe": 16}},
            limit=1,
            output_fields=["name"]
        )
        if results and len(results[0]) > 0:
            match = results[0][0]
            similarity = float(match.distance)
            if similarity >= threshold:
                return {"name": match.entity.get("name"), "similarity": similarity, "match_found": True}
        return {"message": "No match found", "match_found": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during search: {str(e)}")



# Authentication Endpoints
@app.post("/auth/token")
async def login_for_access_token(data: UserLoginModel):
    try:
        # Retrieve user from the database
        user = await load_user(data.username)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Verify password
        if not verify_password(data.password, user.hashedPassword): 
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = manager.create_access_token(
            data={"sub": user.username},
            expires=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException as e:
        print(f"Authentication error: {e.detail}")
        raise
    except Exception as e:
        print(f"Unexpected error during login: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")



@app.post("/register-user/")
async def register_user(user: UserRegistrationModel):
    try:
        hashed_pw = hashed_password(user.password)
        created_user = await db.user.create(
            data={
                "username": user.username,
                "email": user.email,
                "fullName": user.fullName,
                "hashedPassword": hashed_pw,
                "role": user.role
            }
        )
        return {"message": "User registered successfully", "user": created_user}
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")



# main end points - Facial Recognition
@app.post("/register-employee/")
async def register_employee(
    employee: EmployeeRegistrationModel,
    photo: UploadFile,
    user: User = Depends(manager)):
    try:
        photo_bytes = await photo.read()
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        embedding = extract_face_embedding(photo_bytes)

        additional_data = {
            "designation": employee.designation,
            "contactNumber": employee.contactNumber,
            "department": employee.department,
            "description": employee.description
        }
        await save_to_prisma(employee.name, employee.age, employee.gender, photo_base64, "employee", additional_data)
        save_to_milvus(EMPLOYEE_COLLECTION, employee.name, embedding)
        return {"message": "Employee registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

@app.post("/register-visitor/")
async def register_visitor(
    visitor: VisitorRegistrationModel,
    photo: UploadFile,
    user: User = Depends(manager)):
    try:
        photo_bytes = await photo.read()
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        embedding = extract_face_embedding(photo_bytes)

        additional_data = {
            "contact": visitor.contact,
            "purposeOfVisit": visitor.purposeOfVisit,
            "description": visitor.description
        }
        await save_to_prisma(visitor.name, visitor.age, visitor.gender, photo_base64, "visitor", additional_data)
        save_to_milvus(VISITOR_COLLECTION, visitor.name, embedding)
        return {"message": "Visitor registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

@app.post("/recognize-employee/")
async def recognize_employee(
    photo: UploadFile,
    user: User = Depends(manager)):
    try:
        photo_bytes = await photo.read()
        query_embedding = extract_face_embedding(photo_bytes)
        result = search_in_milvus(EMPLOYEE_COLLECTION, query_embedding)
        if result["match_found"]:
            similarity = result["similarity"]
            status = "success" if similarity >= 0.4 else "failed"
            return {
                "name": result["name"],
                "similarity": similarity,
                "status": status,
            }
        return {
            "message": result["message"],
            "status": "failed",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

@app.post("/recognize-visitor/")
async def recognize_visitor(
    photo: UploadFile,
    user: User = Depends(manager)):
    try:
        photo_bytes = await photo.read()
        query_embedding = extract_face_embedding(photo_bytes)
        result = search_in_milvus(VISITOR_COLLECTION, query_embedding)
        if result["match_found"]:
            similarity = result["similarity"]
            status = "success" if similarity >= 0.4 else "failed"
            return {
                "name": result["name"],
                "similarity": similarity,
                "status": status,
            }
        return {
            "message": result["message"],
            "status": "failed",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
