# working code - without authentication
from fastapi import FastAPI, HTTPException, UploadFile, Form, File, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from prisma import Prisma
from prisma.errors import PrismaError
from pymilvus import connections, CollectionSchema, Collection, FieldSchema, DataType, utility
from deepface import DeepFace
from PIL import Image
import numpy as np
import os
import base64
import uvicorn
import asyncio
from datetime import datetime
import pytz
import tempfile
import time
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from auth import AuthService
import logging 


# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

app = FastAPI(
    title="Face Recognition",
    description="Backend for Face Recognition App with Prisma and Milvus",
    version="1.0"
)

@app.get("/")
async def root():
    return {"message": "Face App Backend"}

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

# Initialize components
logger = logging.getLogger("face-app")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Initialize auth service after Prisma client
auth_service = None

@app.on_event("startup")
async def startup():
    global auth_service
    max_retries = 5
    for attempt in range(max_retries):
        try:
            await db.connect()
            print("Connected to PostgreSQL database")
            # Initialize auth service after database connection
            auth_service = AuthService(logger, oauth2_scheme, db)
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

# Help loading the milvus collections
def load_collection(collection_name):
    collection = Collection(name=collection_name)
    collection.load()
    print(f"Collection '{collection_name}' loaded into memory.")



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
            
            
            load_collection(EMPLOYEE_COLLECTION)
            load_collection(VISITOR_COLLECTION)
            
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
        # Save the photo bytes to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(photo_bytes)
            temp_file_path = temp_file.name
        
        # Use DeepFace to detect and extract embeddings
        embedding = DeepFace.represent(
            img_path=temp_file_path,
            model_name=MODEL_NAME,
            enforce_detection=True
        )
        
        # Delete the temporary file
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
            } # photo: UploadFile = File(...),
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

# Authentication endpoints
@app.post("/auth/register")
async def register_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """Register a new user."""
    try:
        await auth_service.register_user(
            username=form_data.username,
            password=form_data.password,
            email=form_data.email, 
            fullName=form_data.fullName,
            role=form_data.role
        )
        return {"message": "User registered successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint to get access token."""
    try:
        if await auth_service.validate_credentials(form_data.username, form_data.password):
            token = await auth_service.generate_token(form_data.username)
            return {"access_token": token, "token_type": "bearer"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

# Middleware to protect routes
async def verify_token(token: str = Depends(oauth2_scheme)):
    if not await auth_service.validate_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

# Protected routes 
@app.post("/register-employee/")
async def register_employee(
    token: str = Depends(verify_token),
    name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    photo: UploadFile = None,
    designation: str = Form(...),
    contactNumber: str = Form(...),
    department: str = Form(...),
    description: str = Form(...)
):
    try:
        photo_bytes = await photo.read()  
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")  # Convert photo to base64
        embedding = extract_face_embedding(photo_bytes)  # Extract the face embedding
        
        additional_data = {
            "designation": designation,
            "contactNumber": contactNumber,
            "department": department,
            "description": description
        }
        await save_to_prisma(name, age, gender, photo_base64, "employee", additional_data)
        save_to_milvus(EMPLOYEE_COLLECTION, name, embedding)  # Save to Milvus
        return {"message": "Employee registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

@app.post("/register-visitor/")
async def register_visitor(
    token: str = Depends(verify_token),
    name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    photo: UploadFile = None,
    contact: str = Form(...),
    purposeOfVisit: str = Form(...),
    description: str = Form(...)
):
    try:
        photo_bytes = await photo.read()  
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")  # Convert photo to base64
        embedding = extract_face_embedding(photo_bytes)  # Extract the face embedding
        
        additional_data = {
            "contact": contact,
            "purposeOfVisit": purposeOfVisit,
            "description": description
        }
        await save_to_prisma(name, age, gender, photo_base64, "visitor", additional_data)
        save_to_milvus(VISITOR_COLLECTION, name, embedding)
        return {"message": "Visitor registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")


@app.post("/recognize-employee/")
async def recognize_employee(
    photo: UploadFile,
    token: str = Depends(verify_token)
):
    try:
        # Read the uploaded photo bytes
        photo_bytes = await photo.read()
        # Extract the face embedding
        query_embedding = extract_face_embedding(photo_bytes)
        # Perform the search in the Milvus collection
        result = search_in_milvus(EMPLOYEE_COLLECTION, query_embedding)
        # Determine the status based on similarity
        if result["match_found"]:
            similarity = result["similarity"]
            status = "success" if similarity >= 0.4 else "failed"
            return {
                "name": result["name"],
                "similarity": similarity,
                "status": status,
            }
        # No match found
        return {
            "message": result["message"],
            "status": "failed",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")
    
    
@app.post("/recognize-visitor/")
async def recognize_visitor(
    photo: UploadFile,
    token: str = Depends(verify_token)
):
    try:
        photo_bytes = await photo.read() 
        query_embedding = extract_face_embedding(photo_bytes)
        result = search_in_milvus(VISITOR_COLLECTION, query_embedding)
        if result["match_found"]:
            similarity = result["similarity"]
            status = "success" if similarity >= 0.4 else "failed"
            return {
                "name" : result["name"],
                "similarity": similarity,
                "status": status,
            }
            
            return {
                "message": result["message"],
                "status" : "failed",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)