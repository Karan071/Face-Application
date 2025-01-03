from fastapi import FastAPI, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pymilvus import connections, Collection, DataType, CollectionSchema, FieldSchema, utility
from deepface import DeepFace
import numpy as np
from io import BytesIO
from PIL import Image, UnidentifiedImageError
import json
import os
import base64
import uvicorn
import time

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

app = FastAPI(
    title="Face Recognition",
    description="Backend for Face Recognition App with Milvus",
    version="0.2"
)

# CORS Settings
origins = ["https://localhost:5174", "https://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Milvus Configuration
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")

def connect_to_milvus():
    attempts = 5
    for attempt in range(attempts):
        try:
            if connections.has_connection("default"):
                connections.remove_connection("default")
            
            print(f"Attempting to connect to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
            connections.connect(
                alias="default",
                host=MILVUS_HOST,
                port=MILVUS_PORT,
                timeout=30
            )
            print(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
            return True
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    raise RuntimeError("Failed to connect to Milvus after several attempts")

connect_to_milvus()

MODEL_NAME = "VGG-Face"

# Milvus collection schema
EMPLOYEE_COLLECTION = "employee_embeddings"
VISITOR_COLLECTION = "visitor_embeddings"

def create_milvus_collection(collection_name):
    try:
        if not utility.has_collection(collection_name):
            schema = CollectionSchema(
                fields=[
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=255),
                    FieldSchema(name="age", dtype=DataType.INT64),
                    FieldSchema(name="gender", dtype=DataType.VARCHAR, max_length=10),
                    FieldSchema(name="photo_base64", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=4096),
                ],
                description=f"{collection_name} for storing embeddings"
            )
            collection = Collection(name=collection_name, schema=schema)
            print(f"Created collection: {collection_name}")

            # Create index with L2 (Euclidean Distance) metric
            index_params = {
                "metric_type": "L2",  # Switched to L2
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            collection.create_index(
                field_name="embedding",
                index_params=index_params,
                timeout=None
            )
            print(f"Created index for collection: {collection_name}")
            
            collection.flush()
            collection.load()
            print(f"Loaded collection: {collection_name}")
        else:
            collection = Collection(collection_name)
            
            if not collection.has_index():
                index_params = {
                    "metric_type": "L2",  # Switched to L2
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128}
                }
                collection.create_index(
                    field_name="embedding",
                    index_params=index_params,
                    timeout=None
                )
                print(f"Created index for existing collection: {collection_name}")
                collection.flush()
            
            collection.load()
            print(f"Loaded existing collection: {collection_name}")
            
        return collection
    except Exception as e:
        print(f"Error in create_milvus_collection: {str(e)}")
        raise RuntimeError(f"Failed to create/load collection '{collection_name}': {str(e)}")

# Initialize Milvus collections
employee_collection = create_milvus_collection(EMPLOYEE_COLLECTION)
visitor_collection = create_milvus_collection(VISITOR_COLLECTION)

@app.get("/")
def backend_init():
    return {"backend": "Backend running successfully with Milvus"}

def preprocess_image(photo_bytes: bytes):
    """Preprocess image: Validate, resize, and normalize."""
    try:
        photo = Image.open(BytesIO(photo_bytes))
        if photo.mode != "RGB":
            photo = photo.convert("RGB")
        photo = photo.resize((224, 224))
        return np.array(photo)
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

def extract_face_embedding(photo_bytes: bytes):
    """Extract face embedding using DeepFace with VGG-Face model."""
    try:
        photo_array = preprocess_image(photo_bytes)
        embedding = DeepFace.represent(
            img_path=photo_array, model_name=MODEL_NAME, enforce_detection=False
        )
        if len(embedding) > 0 and "embedding" in embedding[0]:
            return embedding[0]["embedding"]
        raise ValueError("No embedding found in the model output.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting embedding: {str(e)}")

def save_to_milvus(collection_name, name, age, gender, photo_base64, embedding):
    """Save data to Milvus."""
    collection = Collection(collection_name)
    data = [
        [None],  # Auto ID
        [name],
        [age],
        [gender],
        [photo_base64],
        [embedding]
    ]
    collection.insert(data)

@app.post("/register-employee/")
async def register_employee(
    name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None
):
    try:
        photo_bytes = await photo.read()
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        embedding = extract_face_embedding(photo_bytes)
        save_to_milvus(EMPLOYEE_COLLECTION, name, age, gender, photo_base64, embedding)
        return {"message": "Employee registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during employee registration: {str(e)}")

@app.post("/register-visitor/")
async def register_visitor(
    name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None
):
    try:
        photo_bytes = await photo.read()
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        embedding = extract_face_embedding(photo_bytes)
        save_to_milvus(VISITOR_COLLECTION, name, age, gender, photo_base64, embedding)
        return {"message": "Visitor registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during visitor registration: {str(e)}")

def search_in_milvus(collection_name, query_embedding, threshold=0.85):
    """Search for similar embeddings in Milvus."""
    try:
        collection = Collection(collection_name)
        search_params = {
            "metric_type": "L2",  
            "params": {"nprobe": 10}
        }
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=1,
            output_fields=["name"]
        )
        
        if results and len(results[0]) > 0:
            match = results[0][0]
            if match.distance >= threshold:
                return {"name": match.entity.get("name"), "similarity": float(match.distance)}
        return {"message": "No match found"}
    except Exception as e:
        print(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during search: {str(e)}")

@app.post("/recognize-employee/")
async def recognize_employee(photo: UploadFile):
    try:
        photo_bytes = await photo.read()
        uploaded_embedding = extract_face_embedding(photo_bytes)
        result = search_in_milvus(EMPLOYEE_COLLECTION, uploaded_embedding)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in face recognition: {str(e)}")

@app.post("/recognize-visitor/")
async def recognize_visitor(photo: UploadFile):
    try:
        photo_bytes = await photo.read()
        uploaded_embedding = extract_face_embedding(photo_bytes)
        result = search_in_milvus(VISITOR_COLLECTION, uploaded_embedding, threshold=0.6)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in face recognition: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)


