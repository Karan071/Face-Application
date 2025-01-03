from fastapi import FastAPI, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from prisma import Prisma
from prisma.errors import PrismaError
from pymilvus import connections, Collection, DataType, CollectionSchema, FieldSchema, utility
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

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

app = FastAPI(
    title="Face Recognition",
    description="Backend for Face Recognition App with Prisma and Milvus",
    version="0.5"
)

@app.get("/")
async def root():
    return {"message": "Face App Backend"}

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174"
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

# Milvus Configuration
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
EMPLOYEE_COLLECTION = "employee_embeddings"
VISITOR_COLLECTION = "visitor_embeddings"

MODEL_NAME = "VGG-Face"

# --- Utility Functions for Milvus ---
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

async def save_to_prisma(name: str, age: int, gender: str, photo_base64: str, table: str):
    if table == "employee":
        record = await db.employee.create(
            data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
        )
    elif table == "visitor":
        record = await db.visitor.create(
            data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
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

# --- API Endpoints ---
@app.post("/register-employee/")
async def register_employee(name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None):
    try:
        photo_bytes = await photo.read()
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        embedding = extract_face_embedding(photo_bytes)
        await save_to_prisma(name, age, gender, photo_base64, "employee")
        save_to_milvus(EMPLOYEE_COLLECTION, name, embedding)
        return {"message": "Employee registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

@app.post("/register-visitor/")
async def register_visitor(name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None):
    try:
        photo_bytes = await photo.read()
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        embedding = extract_face_embedding(photo_bytes)
        await save_to_prisma(name, age, gender, photo_base64, "visitor")
        save_to_milvus(VISITOR_COLLECTION, name, embedding)
        return {"message": "Visitor registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

@app.post("/recognize-employee/")
async def recognize_employee(photo: UploadFile):
    try:
        photo_bytes = await photo.read()
        query_embedding = extract_face_embedding(photo_bytes)
        result = search_in_milvus(EMPLOYEE_COLLECTION, query_embedding)
        if result["match_found"]:
            return {"name": result["name"], "similarity": result["similarity"]}
        return {"message": result["message"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

@app.post("/recognize-visitor/")
async def recognize_visitor(photo: UploadFile):
    try:
        photo_bytes = await photo.read()
        query_embedding = extract_face_embedding(photo_bytes)
        result = search_in_milvus(VISITOR_COLLECTION, query_embedding)
        if result["match_found"]:
            return {"name": result["name"], "similarity": result["similarity"]}
        return {"message": result["message"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)


---------------------
# from fastapi import FastAPI, HTTPException, UploadFile, Form
# from fastapi.middleware.cors import CORSMiddleware
# from prisma import Prisma
# from prisma.errors import PrismaError
# from pymilvus import connections, Collection, DataType, CollectionSchema, FieldSchema, utility
# from deepface import DeepFace
# from mtcnn.mtcnn import MTCNN  
# import numpy as np
# from io import BytesIO
# from PIL import Image, UnidentifiedImageError
# import json
# import os
# import base64
# import time
# import uvicorn
# import asyncio
# from datetime import datetime
# import pytz

# # Suppress TensorFlow warnings
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# app = FastAPI(
#     title="Face Recognition",
#     description="Backend for Face Recognition App with Prisma and Milvus",
#     version="0.3"
# )

# @app.get("/")
# async def root():
#     print("Root endpoint called")
#     return {"message": "Face App Backend"}

# origins = [
#     "http://localhost:5173",
#     "http://localhost:5174",
#     "http://localhost:8000",
#     "http://127.0.0.1:8000",
#     "http://127.0.0.1:5173",
#     "http://127.0.0.1:5174"
# ]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize Prisma client
# db = Prisma()

# @app.on_event("startup")
# async def startup():
#     """Initialize connections on startup."""
#     max_retries = 5
#     for attempt in range(max_retries):
#         try:
#             await db.connect()
#             print("Connected to PostgreSQL database")
#             break
#         except PrismaError as e:
#             if attempt == max_retries - 1:
#                 raise RuntimeError(f"Failed to connect to database after {max_retries} attempts")
#             print(f"Database connection attempt {attempt + 1} failed, retrying...")
#             await asyncio.sleep(5)
    
#     # Connect to Milvus
#     connect_to_milvus()
#     global employee_collection, visitor_collection
#     employee_collection = create_milvus_collection(EMPLOYEE_COLLECTION)
#     visitor_collection = create_milvus_collection(VISITOR_COLLECTION)

# @app.on_event("shutdown")
# async def shutdown():
#     """Clean up connections on shutdown."""
#     await db.disconnect()
#     if connections.has_connection("default"):
#         connections.remove_connection("default")

# # Milvus Configuration
# MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
# MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
# EMPLOYEE_COLLECTION = "employee_embeddings"
# VISITOR_COLLECTION = "visitor_embeddings"

# MODEL_NAME = "VGG-Face"

# # Initialize MTCNN for face detection
# detector = MTCNN()

# # --- Utility Functions for Milvus ---
# def connect_to_milvus():
#     """Connect to Milvus with retries for robustness."""
#     attempts = 5
#     for attempt in range(attempts):
#         try:
#             if connections.has_connection("default"):
#                 connections.remove_connection("default")
            
#             print(f"Attempting to connect to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
#             connections.connect(
#                 alias="default",
#                 host=MILVUS_HOST,
#                 port=MILVUS_PORT,
#                 timeout=60
#             )
#             print(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
#             return True
#         except Exception as e:
#             print(f"Connection attempt {attempt + 1} failed: {e}")
#             time.sleep(5)
#     raise RuntimeError("Failed to connect to Milvus after several attempts")

# def create_milvus_collection(collection_name):
#     """Create a Milvus collection for embeddings."""
#     try:
#         if not utility.has_collection(collection_name):
#             schema = CollectionSchema(
#                 fields=[
#                     FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
#                     FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=255),
#                     FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=4096),
#                 ],
#                 description=f"{collection_name} for storing embeddings"
#             )
#             collection = Collection(name=collection_name, schema=schema)
#             print(f"Created collection: {collection_name}")

#             index_params = {
#                 "metric_type": "IP",
#                 "index_type": "IVF_FLAT",
#                 "params": {"nlist": 128}
#             }
#             collection.create_index(
#                 field_name="embedding",
#                 index_params=index_params,
#                 timeout=None
#             )
#             print(f"Created index for collection: {collection_name}")
            
#             collection.flush()
#             collection.load()
#         else:
#             collection = Collection(collection_name)
#             collection.load()
#         return collection
#     except Exception as e:
#         raise RuntimeError(f"Failed to create/load collection '{collection_name}': {str(e)}")

# # --- Face Embedding Utilities ---
# def preprocess_image_with_mtcnn(photo_bytes: bytes):
#     """
#     Detect, align, resize, and normalize a face using MTCNN.
#     """
#     try:
#         # Load the image from bytes
#         photo = Image.open(BytesIO(photo_bytes))
#         if photo.mode != "RGB":
#             photo = photo.convert("RGB")
#         photo_array = np.array(photo)

#         # Detect faces using MTCNN
#         faces = detector.detect_faces(photo_array)
#         if len(faces) == 0:
#             raise HTTPException(status_code=400, detail="No face detected in the image.")

#         # Extract the first detected face
#         x, y, w, h = faces[0]['box']
#         face = photo_array[y:y+h, x:x+w]

#         # Resize and normalize the cropped face
#         face_image = Image.fromarray(face).resize((224, 224))
#         face_array = np.array(face_image) / 255.0  # Normalize to [0, 1]

#         # Normalize to unit vector
#         face_array = face_array / np.linalg.norm(face_array)  # Normalize to unit vector
#         return face_array

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during face preprocessing: {str(e)}")


# def extract_face_embedding(photo_bytes: bytes):
#     """
#     Extract face embedding using DeepFace with preprocessing via MTCNN.
#     """
#     try:
#         face_array = preprocess_image_with_mtcnn(photo_bytes)
#         embedding = DeepFace.represent(
#             img_path=face_array, 
#             model_name=MODEL_NAME, 
#             enforce_detection=False
#         )
#         return embedding[0]["embedding"]
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error extracting embedding: {str(e)}")

# def format_datetime(dt: datetime) -> str:
#     ist = pytz.timezone('Asia/Kolkata')
#     dt_ist = dt.astimezone(ist)
#     return dt_ist.strftime("%B %d, %Y at %I:%M %p IST")

# def save_to_milvus(collection_name, name, embedding):
#     collection = Collection(collection_name)
    
#     # No need to normalize again since it's already done
#     data = [[name], [embedding.tolist()]]
#     collection.insert(data)
#     collection.flush()

# async def save_to_prisma(name: str, age: int, gender: str, photo_base64: str, table: str):
#     """Save user details in Prisma database."""
#     if table == "employee":
#         record = await db.employee.create(
#             data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
#         )
#     elif table == "visitor":
#         record = await db.visitor.create(
#             data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
#         )
#     return {
#         **record.model_dump(),
#         "createdAt": format_datetime(record.createdAt),
#         "updatedAt": format_datetime(record.updatedAt)
#     }

# def search_in_milvus(collection_name, query_embedding, threshold=0.6):
#     """Search for similar embeddings using cosine similarity."""
#     try:
#         query_embedding = np.array(query_embedding) / np.linalg.norm(query_embedding)
#         collection = Collection(collection_name)
#         results = collection.search(
#             data=[query_embedding.tolist()],
#             anns_field="embedding",
#             param={"metric_type": "IP", "params": {"nprobe": 16}},
#             limit=1,
#             output_fields=["name"]
#         )
#         if results and len(results[0]) > 0:
#             match = results[0][0]
#             similarity = float(match.distance)
#             if similarity >= threshold:
#                 return {"name": match.entity.get("name"), "similarity": similarity, "match_found": True}
#         return {"message": "No match found", "match_found": False}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during search: {str(e)}")

# # --- Endpoints ---
# @app.post("/register-employee/")
# async def register_employee(name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None):
#     try:
#         photo_bytes = await photo.read()
#         photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
#         embedding = extract_face_embedding(photo_bytes)
#         await save_to_prisma(name, age, gender, photo_base64, "employee")
#         save_to_milvus(EMPLOYEE_COLLECTION, name, embedding)
#         return {"message": "Employee registered successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

# @app.post("/register-visitor/")
# async def register_visitor(name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None):
#     try:
#         photo_bytes = await photo.read()
#         photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
#         embedding = extract_face_embedding(photo_bytes)
#         await save_to_prisma(name, age, gender, photo_base64, "visitor")
#         save_to_milvus(VISITOR_COLLECTION, name, embedding)
#         return {"message": "Visitor registered successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

# @app.post("/recognize-employee/")
# async def recognize_employee(photo: UploadFile):
#     try:
#         photo_bytes = await photo.read()
#         query_embedding = extract_face_embedding(photo_bytes)
#         result = search_in_milvus(EMPLOYEE_COLLECTION, query_embedding)
#         if result["match_found"]:
#             return {"name": result["name"], "similarity": result["similarity"]}
#         return {"message": result["message"]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

# @app.post("/recognize-visitor/")
# async def recognize_visitor(photo: UploadFile):
#     try:
#         photo_bytes = await photo.read()
#         query_embedding = extract_face_embedding(photo_bytes)
#         result = search_in_milvus(VISITOR_COLLECTION, query_embedding)
#         if result["match_found"]:
#             return {"name": result["name"], "similarity": result["similarity"]}
#         return {"message": result["message"]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=8000)

# from fastapi import FastAPI, HTTPException, UploadFile, Form
# from fastapi.middleware.cors import CORSMiddleware
# from prisma import Prisma
# from prisma.errors import PrismaError
# from pymilvus import connections, Collection, DataType, CollectionSchema, FieldSchema, utility
# from deepface import DeepFace
# from mtcnn.mtcnn import MTCNN
# import numpy as np
# from io import BytesIO
# from PIL import Image
# import json
# import os
# import base64
# import time
# import uvicorn
# import asyncio
# from datetime import datetime
# import pytz
# import tempfile
# import tensorflow as tf

# # Suppress TensorFlow warnings
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
# tf.get_logger().setLevel('ERROR')

# app = FastAPI(
#     title="Face Recognition",
#     description="Backend for Face Recognition App with Prisma and Milvus",
#     version="0.3"
# )

# @app.get("/")
# async def root():
#     return {"message": "Face App Backend"}

# origins = [
#     "http://localhost:5173",
#     "http://localhost:5174",
#     "http://localhost:8000",
#     "http://127.0.0.1:8000",
#     "http://127.0.0.1:5173",
#     "http://127.0.0.1:5174"
# ]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize Prisma client
# db = Prisma()

# @app.on_event("startup")
# async def startup():
#     max_retries = 5
#     for attempt in range(max_retries):
#         try:
#             await db.connect()
#             print("Connected to PostgreSQL database")
#             break
#         except PrismaError as e:
#             if attempt == max_retries - 1:
#                 raise RuntimeError(f"Failed to connect to database after {max_retries} attempts")
#             print(f"Database connection attempt {attempt + 1} failed, retrying...")
#             await asyncio.sleep(5)
    
#     connect_to_milvus()
#     global employee_collection, visitor_collection
#     employee_collection = create_milvus_collection(EMPLOYEE_COLLECTION)
#     visitor_collection = create_milvus_collection(VISITOR_COLLECTION)

# @app.on_event("shutdown")
# async def shutdown():
#     await db.disconnect()
#     if connections.has_connection("default"):
#         connections.remove_connection("default")

# # Milvus Configuration
# MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
# MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
# EMPLOYEE_COLLECTION = "employee_embeddings"
# VISITOR_COLLECTION = "visitor_embeddings"

# MODEL_NAME = "VGG-Face"
# detector = MTCNN()

# # --- Utility Functions for Milvus ---
# def connect_to_milvus():
#     attempts = 5
#     for attempt in range(attempts):
#         try:
#             if connections.has_connection("default"):
#                 connections.remove_connection("default")
            
#             connections.connect(
#                 alias="default",
#                 host=MILVUS_HOST,
#                 port=MILVUS_PORT,
#                 timeout=60
#             )
#             print(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
#             return True
#         except Exception as e:
#             print(f"Connection attempt {attempt + 1} failed: {e}")
#             time.sleep(5)
#     raise RuntimeError("Failed to connect to Milvus after several attempts")

# def create_milvus_collection(collection_name):
#     try:
#         if not utility.has_collection(collection_name):
#             schema = CollectionSchema(
#                 fields=[
#                     FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
#                     FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=255),
#                     FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=4096),
#                 ],
#                 description=f"{collection_name} for storing embeddings"
#             )
#             collection = Collection(name=collection_name, schema=schema)
#             index_params = {
#                 "metric_type": "IP",
#                 "index_type": "IVF_FLAT",
#                 "params": {"nlist": 128}
#             }
#             collection.create_index(field_name="embedding", index_params=index_params)
#             collection.flush()
#             collection.load()
#         else:
#             collection = Collection(collection_name)
#             collection.load()
#         return collection
#     except Exception as e:
#         raise RuntimeError(f"Failed to create/load collection '{collection_name}': {str(e)}")

# # --- Face Embedding Utilities ---
# # def preprocess_image_with_mtcnn(photo_bytes: bytes):
# #     """
# #     Detect, crop, normalize, and flatten the face using MTCNN.
# #     """
# #     try:
# #         photo = Image.open(BytesIO(photo_bytes))
# #         if photo.mode != "RGB":
# #             photo = photo.convert("RGB")
# #         photo_array = np.array(photo)
# #         faces = detector.detect_faces(photo_array)
# #         if len(faces) == 0:
# #             raise HTTPException(status_code=400, detail="No face detected in the image.")
# #         x, y, width, height = faces[0]['box']
# #         face_cropped = photo_array[y:y+height, x:x+width]
# #         face_cropped_normalized = face_cropped.astype('float32') / 255.0
# #         face_cropped_flattened = face_cropped_normalized.flatten()
# #         return face_cropped_flattened
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Error during face preprocessing: {str(e)}")

# def preprocess_image_with_mtcnn(photo_bytes: bytes):
#     """
#     Detect, crop, normalize, and resize the face using MTCNN.
#     """
#     try:
#         # Load the image from bytes
#         photo = Image.open(BytesIO(photo_bytes))
#         if photo.mode != "RGB":
#             photo = photo.convert("RGB")
#         photo_array = np.array(photo)
        
#         # Detect faces using MTCNN
#         faces = detector.detect_faces(photo_array)
#         if len(faces) == 0:
#             raise HTTPException(status_code=400, detail="No face detected in the image.")
        
#         # Extract the first detected face
#         x, y, width, height = faces[0]['box']
#         face_cropped = photo_array[y:y+height, x:x+width]
        
#         # Resize the cropped face to 224x224
#         face_resized = Image.fromarray(face_cropped).resize((224, 224))
        
#         # Normalize pixel values to [0, 1]
#         face_normalized = np.array(face_resized).astype('float32') / 255.0
        
#         return face_normalized
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during face preprocessing: {str(e)}")


# # def extract_face_embedding(photo_bytes: bytes):
# #     try:
# #         face_array = preprocess_image_with_mtcnn(photo_bytes)
# #         with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
# #             temp_file_path = temp_file.name
# #         embedding = DeepFace.represent(
# #             img_path=temp_file_path, 
# #             model_name=MODEL_NAME, 
# #             enforce_detection=False
# #         )
# #         return embedding[0]["embedding"]
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Error extracting embedding: {str(e)}")

# # def extract_face_embedding(photo_bytes: bytes):
# #     """
# #     Extract face embedding using DeepFace with preprocessing via MTCNN.
# #     """
# #     try:
# #         # Preprocess image to get cropped and normalized face
# #         face_cropped_flattened = preprocess_image_with_mtcnn(photo_bytes)
        
# #         # Save the processed image as a temporary file
# #         with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
# #             # Convert the 1D flattened array back to a 2D image
# #             face_image = (face_cropped_flattened * 255).astype(np.uint8).reshape((224, 224, 3))
# #             face_pil = Image.fromarray(face_image)
# #             face_pil.save(temp_file.name)
# #             temp_file_path = temp_file.name
        
# #         # Pass the file path to DeepFace
# #         embedding = DeepFace.represent(
# #             img_path=temp_file_path,
# #             model_name=MODEL_NAME,
# #             enforce_detection=False
# #         )
        
# #         # Delete the temporary file
# #         os.remove(temp_file_path)
        
# #         return embedding[0]["embedding"]
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Error extracting embedding: {str(e)}")

# def extract_face_embedding(photo_bytes: bytes):
#     """
#     Extract face embedding using DeepFace with preprocessing via MTCNN.
#     """
#     try:
#         # Preprocess image to get cropped and normalized face
#         face_normalized = preprocess_image_with_mtcnn(photo_bytes)
        
#         # Expand dimensions to add batch axis
#         face_normalized = np.expand_dims(face_normalized, axis=0)
        
#         # Save the processed image as a temporary file
#         with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
#             face_image = (face_normalized[0] * 255).astype(np.uint8)  # Remove batch dimension for saving
#             face_pil = Image.fromarray(face_image)
#             face_pil.save(temp_file.name)
#             temp_file_path = temp_file.name
        
#         # Pass the file path to DeepFace
#         embedding = DeepFace.represent(
#             img_path=temp_file_path,
#             model_name=MODEL_NAME,
#             enforce_detection=False
#         )
        
#         # Delete the temporary file
#         os.remove(temp_file_path)
        
#         return embedding[0]["embedding"]
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error extracting embedding: {str(e)}")



# def format_datetime(dt: datetime) -> str:
#     ist = pytz.timezone('Asia/Kolkata')
#     dt_ist = dt.astimezone(ist)
#     return dt_ist.strftime("%B %d, %Y at %I:%M %p IST")

# def save_to_milvus(collection_name, name, embedding):
#     collection = Collection(collection_name)
#     data = [[name], [embedding.tolist()]]
#     collection.insert(data)
#     collection.flush()

# async def save_to_prisma(name: str, age: int, gender: str, photo_base64: str, table: str):
#     if table == "employee":
#         record = await db.employee.create(
#             data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
#         )
#     elif table == "visitor":
#         record = await db.visitor.create(
#             data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
#         )
#     return {
#         **record.model_dump(),
#         "createdAt": format_datetime(record.createdAt),
#         "updatedAt": format_datetime(record.updatedAt)
#     }

# def search_in_milvus(collection_name, query_embedding, threshold=0.6):
#     try:
#         query_embedding = np.array(query_embedding) / np.linalg.norm(query_embedding)
#         collection = Collection(collection_name)
#         results = collection.search(
#             data=[query_embedding.tolist()],
#             anns_field="embedding",
#             param={"metric_type": "IP", "params": {"nprobe": 16}},
#             limit=1,
#             output_fields=["name"]
#         )
#         if results and len(results[0]) > 0:
#             match = results[0][0]
#             similarity = float(match.distance)
#             if similarity >= threshold:
#                 return {"name": match.entity.get("name"), "similarity": similarity, "match_found": True}
#         return {"message": "No match found", "match_found": False}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during search: {str(e)}")

# @app.post("/register-employee/")
# async def register_employee(name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None):
#     try:
#         photo_bytes = await photo.read()
#         photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
#         embedding = extract_face_embedding(photo_bytes)
#         await save_to_prisma(name, age, gender, photo_base64, "employee")
#         save_to_milvus(EMPLOYEE_COLLECTION, name, embedding)
#         return {"message": "Employee registered successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

# @app.post("/register-visitor/")
# async def register_visitor(name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None):
#     try:
#         photo_bytes = await photo.read()
#         photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
#         embedding = extract_face_embedding(photo_bytes)
#         await save_to_prisma(name, age, gender, photo_base64, "visitor")
#         save_to_milvus(VISITOR_COLLECTION, name, embedding)
#         return {"message": "Visitor registered successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

# @app.post("/recognize-employee/")
# async def recognize_employee(photo: UploadFile):
#     try:
#         photo_bytes = await photo.read()
#         query_embedding = extract_face_embedding(photo_bytes)
#         result = search_in_milvus(EMPLOYEE_COLLECTION, query_embedding)
#         if result["match_found"]:
#             return {"name": result["name"], "similarity": result["similarity"]}
#         return {"message": result["message"]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

# @app.post("/recognize-visitor/")
# async def recognize_visitor(photo: UploadFile):
#     try:
#         photo_bytes = await photo.read()
#         query_embedding = extract_face_embedding(photo_bytes)
#         result = search_in_milvus(VISITOR_COLLECTION, query_embedding)
#         if result["match_found"]:
#             return {"name": result["name"], "similarity": result["similarity"]}
#         return {"message": result["message"]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=8000)





# from fastapi import FastAPI, HTTPException, UploadFile, Form
# from fastapi.middleware.cors import CORSMiddleware
# from prisma import Prisma
# from prisma.errors import PrismaError
# from pymilvus import connections, Collection, DataType, CollectionSchema, FieldSchema, utility
# from deepface import DeepFace
# from PIL import Image
# import numpy as np
# import os
# import base64
# import uvicorn
# import asyncio
# from datetime import datetime
# import pytz
# import tempfile
# import tensorflow as tf

# # Suppress TensorFlow warnings
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
# tf.get_logger().setLevel('ERROR')

# app = FastAPI(
#     title="Face Recognition",
#     description="Backend for Face Recognition App with Prisma and Milvus",
#     version="0.4"
# )

# @app.get("/")
# async def root():
#     return {"message": "Face App Backend"}

# origins = [
#     "http://localhost:5173",
#     "http://localhost:5174",
#     "http://localhost:8000",
#     "http://127.0.0.1:8000",
#     "http://127.0.0.1:5173",
#     "http://127.0.0.1:5174"
# ]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize Prisma client
# db = Prisma()

# @app.on_event("startup")
# async def startup():
#     max_retries = 5
#     for attempt in range(max_retries):
#         try:
#             await db.connect()
#             print("Connected to PostgreSQL database")
#             break
#         except PrismaError as e:
#             if attempt == max_retries - 1:
#                 raise RuntimeError(f"Failed to connect to database after {max_retries} attempts")
#             print(f"Database connection attempt {attempt + 1} failed, retrying...")
#             await asyncio.sleep(5)
    
#     connect_to_milvus()
#     global employee_collection, visitor_collection
#     employee_collection = create_milvus_collection(EMPLOYEE_COLLECTION)
#     visitor_collection = create_milvus_collection(VISITOR_COLLECTION)

#     # Preload DeepFace model
#     preload_deepface_model()

# @app.on_event("shutdown")
# async def shutdown():
#     await db.disconnect()
#     if connections.has_connection("default"):
#         connections.remove_connection("default")

# # Milvus Configuration
# MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
# MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
# EMPLOYEE_COLLECTION = "employee_embeddings"
# VISITOR_COLLECTION = "visitor_embeddings"

# MODEL_NAME = "VGG-Face"

# # --- Utility Functions for Milvus ---
# def connect_to_milvus():
#     attempts = 5
#     for attempt in range(attempts):
#         try:
#             if connections.has_connection("default"):
#                 connections.remove_connection("default")
            
#             connections.connect(
#                 alias="default",
#                 host=MILVUS_HOST,
#                 port=MILVUS_PORT,
#                 timeout=60
#             )
#             print(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
#             return True
#         except Exception as e:
#             print(f"Connection attempt {attempt + 1} failed: {e}")
#             time.sleep(5)
#     raise RuntimeError("Failed to connect to Milvus after several attempts")

# def create_milvus_collection(collection_name):
#     try:
#         if not utility.has_collection(collection_name):
#             schema = CollectionSchema(
#                 fields=[
#                     FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
#                     FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=255),
#                     FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=4096),
#                 ],
#                 description=f"{collection_name} for storing embeddings"
#             )
#             collection = Collection(name=collection_name, schema=schema)
#             index_params = {
#                 "metric_type": "IP",
#                 "index_type": "IVF_FLAT",
#                 "params": {"nlist": 128}
#             }
#             collection.create_index(field_name="embedding", index_params=index_params)
#             collection.flush()
#             collection.load()
#         else:
#             collection = Collection(collection_name)
#             collection.load()
#         return collection
#     except Exception as e:
#         raise RuntimeError(f"Failed to create/load collection '{collection_name}': {str(e)}")

# def preload_deepface_model():
#     """
#     Preload DeepFace model to resolve lazy initialization issues.
#     """
#     try:
#         dummy_image = np.zeros((224, 224, 3))
#         dummy_image_path = os.path.join(tempfile.gettempdir(), "dummy_image.jpg")
#         Image.fromarray((dummy_image * 255).astype(np.uint8)).save(dummy_image_path)
#         DeepFace.represent(img_path=dummy_image_path, model_name=MODEL_NAME, enforce_detection=True)
#         os.remove(dummy_image_path)
#         print("DeepFace model preloaded successfully")
#     except Exception as e:
#         print(f"Error during DeepFace model preload: {str(e)}")

# # --- Face Embedding Utilities ---
# def extract_face_embedding(photo_bytes: bytes):
#     """
#     Extract face embedding using DeepFace with built-in detection.
#     """
#     try:
#         # Save the photo bytes to a temporary file
#         with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
#             temp_file.write(photo_bytes)
#             temp_file_path = temp_file.name
        
#         # Use DeepFace to detect and extract embeddings
#         embedding = DeepFace.represent(
#             img_path=temp_file_path,
#             model_name=MODEL_NAME,
#             enforce_detection=True
#         )
        
#         # Delete the temporary file
#         os.remove(temp_file_path)
        
#         return embedding[0]["embedding"]
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error extracting embedding: {str(e)}")

# def format_datetime(dt: datetime) -> str:
#     ist = pytz.timezone('Asia/Kolkata')
#     dt_ist = dt.astimezone(ist)
#     return dt_ist.strftime("%B %d, %Y at %I:%M %p IST")

# def save_to_milvus(collection_name, name, embedding):
#     collection = Collection(collection_name)
#     data = [[name], [embedding]]
#     collection.insert(data)
#     collection.flush()

# async def save_to_prisma(name: str, age: int, gender: str, photo_base64: str, table: str):
#     if table == "employee":
#         record = await db.employee.create(
#             data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
#         )
#     elif table == "visitor":
#         record = await db.visitor.create(
#             data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
#         )
#     return {
#         **record.model_dump(),
#         "createdAt": format_datetime(record.createdAt),
#         "updatedAt": format_datetime(record.updatedAt)
#     }

# def search_in_milvus(collection_name, query_embedding, threshold=0.6):
#     try:
#         query_embedding = np.array(query_embedding) / np.linalg.norm(query_embedding)
#         collection = Collection(collection_name)
#         results = collection.search(
#             data=[query_embedding.tolist()],
#             anns_field="embedding",
#             param={"metric_type": "IP", "params": {"nprobe": 16}},
#             limit=1,
#             output_fields=["name"]
#         )
#         if results and len(results[0]) > 0:
#             match = results[0][0]
#             similarity = float(match.distance)
#             if similarity >= threshold:
#                 return {"name": match.entity.get("name"), "similarity": similarity, "match_found": True}
#         return {"message": "No match found", "match_found": False}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during search: {str(e)}")

# @app.post("/register-employee/")
# async def register_employee(name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None):
#     try:
#         photo_bytes = await photo.read()
#         photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
#         embedding = extract_face_embedding(photo_bytes)
#         await save_to_prisma(name, age, gender, photo_base64, "employee")
#         save_to_milvus(EMPLOYEE_COLLECTION, name, embedding)
#         return {"message": "Employee registered successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

# @app.post("/register-visitor/")
# async def register_visitor(name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None):
#     try:
#         photo_bytes = await photo.read()
#         photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
#         embedding = extract_face_embedding(photo_bytes)
#         await save_to_prisma(name, age, gender, photo_base64, "visitor")
#         save_to_milvus(VISITOR_COLLECTION, name, embedding)
#         return {"message": "Visitor registered successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

# @app.post("/recognize-employee/")
# async def recognize_employee(photo: UploadFile):
#     try:
#         photo_bytes = await photo.read()
#         query_embedding = extract_face_embedding(photo_bytes)
#         result = search_in_milvus(EMPLOYEE_COLLECTION, query_embedding)
#         if result["match_found"]:
#             return {"name": result["name"], "similarity": result["similarity"]}
#         return {"message": result["message"]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

# @app.post("/recognize-visitor/")
# async def recognize_visitor(photo: UploadFile):
#     try:
#         photo_bytes = await photo.read()
#         query_embedding = extract_face_embedding(photo_bytes)
#         result = search_in_milvus(VISITOR_COLLECTION, query_embedding)
#         if result["match_found"]:
#             return {"name": result["name"], "similarity": result["similarity"]}
#         return {"message": result["message"]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=8000)




# code without the new fields
# from fastapi import FastAPI, HTTPException, UploadFile, Form
# from fastapi.middleware.cors import CORSMiddleware
# from prisma import Prisma
# from prisma.errors import PrismaError
# from pymilvus import connections, Collection, DataType, CollectionSchema, FieldSchema, utility
# from deepface import DeepFace
# from PIL import Image
# import numpy as np
# import os
# import base64
# import uvicorn
# import asyncio
# from datetime import datetime
# import pytz
# import tempfile
# import time

# # Suppress TensorFlow warnings
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# app = FastAPI(
#     title="Face Recognition",
#     description="Backend for Face Recognition App with Prisma and Milvus",
#     version="0.5"
# )

# @app.get("/")
# async def root():
#     return {"message": "Face App Backend"}

# origins = [
#     "http://localhost:5173",
#     "http://localhost:5174",
#     "http://localhost:8000",
#     "http://127.0.0.1:8000",
#     "http://127.0.0.1:5173",
#     "http://127.0.0.1:5174"
# ]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize Prisma client
# db = Prisma()

# @app.on_event("startup")
# async def startup():
#     max_retries = 5
#     for attempt in range(max_retries):
#         try:
#             await db.connect()
#             print("Connected to PostgreSQL database")
#             break
#         except PrismaError as e:
#             if attempt == max_retries - 1:
#                 raise RuntimeError(f"Failed to connect to database after {max_retries} attempts")
#             print(f"Database connection attempt {attempt + 1} failed, retrying...")
#             await asyncio.sleep(5)
    
#     connect_to_milvus()
#     preload_deepface_model()

# @app.on_event("shutdown")
# async def shutdown():
#     await db.disconnect()
#     if connections.has_connection("default"):
#         connections.remove_connection("default")

# # Milvus Configuration
# MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
# MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
# EMPLOYEE_COLLECTION = "employee_embeddings"
# VISITOR_COLLECTION = "visitor_embeddings"

# MODEL_NAME = "VGG-Face"

# # --- Utility Functions for Milvus ---
# def connect_to_milvus():
#     attempts = 5
#     for attempt in range(attempts):
#         try:
#             if connections.has_connection("default"):
#                 connections.remove_connection("default")
            
#             connections.connect(
#                 alias="default",
#                 host=MILVUS_HOST,
#                 port=MILVUS_PORT,
#                 timeout=60
#             )
#             print(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
#             return True
#         except Exception as e:
#             print(f"Connection attempt {attempt + 1} failed: {e}")
#             time.sleep(5)
#     raise RuntimeError("Failed to connect to Milvus after several attempts")

# def preload_deepface_model():
#     """
#     Preload DeepFace model to resolve lazy initialization issues.
#     """
#     try:
#         dummy_image = np.zeros((224, 224, 3), dtype=np.uint8)
#         dummy_image_path = os.path.join(tempfile.gettempdir(), "dummy_image.jpg")
#         Image.fromarray(dummy_image).save(dummy_image_path)
#         DeepFace.represent(img_path=dummy_image_path, model_name=MODEL_NAME, enforce_detection=False)
#         os.remove(dummy_image_path)
#         print("DeepFace model preloaded successfully")
#     except Exception as e:
#         print(f"Error during DeepFace model preload: {str(e)}")

# # --- Face Embedding Utilities ---
# def extract_face_embedding(photo_bytes: bytes):
#     """
#     Extract face embedding using DeepFace with built-in detection.
#     """
#     try:
#         # Save the photo bytes to a temporary file
#         with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
#             temp_file.write(photo_bytes)
#             temp_file_path = temp_file.name
        
#         # Use DeepFace to detect and extract embeddings
#         embedding = DeepFace.represent(
#             img_path=temp_file_path,
#             model_name=MODEL_NAME,
#             enforce_detection=True
#         )
        
#         # Delete the temporary file
#         os.remove(temp_file_path)
        
#         return embedding[0]["embedding"]
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error extracting embedding: {str(e)}")

# def format_datetime(dt: datetime) -> str:
#     ist = pytz.timezone('Asia/Kolkata')
#     dt_ist = dt.astimezone(ist)
#     return dt_ist.strftime("%B %d, %Y at %I:%M %p IST")

# # Milvus and Prisma Operations
# def save_to_milvus(collection_name, name, embedding):
#     collection = Collection(collection_name)
#     data = [[name], [embedding]]
#     collection.insert(data)
#     collection.flush()

# async def save_to_prisma(name: str, age: int, gender: str, photo_base64: str, table: str):
#     if table == "employee":
#         record = await db.employee.create(
#             data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
#         )
#     elif table == "visitor":
#         record = await db.visitor.create(
#             data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
#         )
#     return {
#         **record.model_dump(),
#         "createdAt": format_datetime(record.createdAt),
#         "updatedAt": format_datetime(record.updatedAt)
#     }

# def search_in_milvus(collection_name, query_embedding, threshold=0.6):
#     try:
#         query_embedding = np.array(query_embedding) / np.linalg.norm(query_embedding)
#         collection = Collection(collection_name)
#         results = collection.search(
#             data=[query_embedding.tolist()],
#             anns_field="embedding",
#             param={"metric_type": "IP", "params": {"nprobe": 16}},
#             limit=1,
#             output_fields=["name"]
#         )
#         if results and len(results[0]) > 0:
#             match = results[0][0]
#             similarity = float(match.distance)
#             if similarity >= threshold:
#                 return {"name": match.entity.get("name"), "similarity": similarity, "match_found": True}
#         return {"message": "No match found", "match_found": False}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during search: {str(e)}")

# # --- API Endpoints ---
# @app.post("/register-employee/")
# async def register_employee(name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None):
#     try:
#         photo_bytes = await photo.read()
#         photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
#         embedding = extract_face_embedding(photo_bytes)
#         await save_to_prisma(name, age, gender, photo_base64, "employee")
#         save_to_milvus(EMPLOYEE_COLLECTION, name, embedding)
#         return {"message": "Employee registered successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

# @app.post("/register-visitor/")
# async def register_visitor(name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None):
#     try:
#         photo_bytes = await photo.read()
#         photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
#         embedding = extract_face_embedding(photo_bytes)
#         await save_to_prisma(name, age, gender, photo_base64, "visitor")
#         save_to_milvus(VISITOR_COLLECTION, name, embedding)
#         return {"message": "Visitor registered successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

# @app.post("/recognize-employee/")
# async def recognize_employee(photo: UploadFile):
#     try:
#         photo_bytes = await photo.read()
#         query_embedding = extract_face_embedding(photo_bytes)
#         result = search_in_milvus(EMPLOYEE_COLLECTION, query_embedding)
#         if result["match_found"]:
#             return {"name": result["name"], "similarity": result["similarity"]}
#         return {"message": result["message"]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

# @app.post("/recognize-visitor/")
# async def recognize_visitor(photo: UploadFile):
#     try:
#         photo_bytes = await photo.read()
#         query_embedding = extract_face_embedding(photo_bytes)
#         result = search_in_milvus(VISITOR_COLLECTION, query_embedding)
#         if result["match_found"]:
#             return {"name": result["name"], "similarity": result["similarity"]}
#         return {"message": result["message"]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=8000)

--------main.py content-------
from fastapi import FastAPI, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from prisma import Prisma
from prisma.errors import PrismaError
from pymilvus import connections, Collection, DataType, CollectionSchema, FieldSchema, utility
from deepface import DeepFace
import numpy as np
from io import BytesIO
from PIL import Image, UnidentifiedImageError
import json
import os
import base64
import time
import uvicorn
import asyncio
from datetime import datetime
import pytz

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

app = FastAPI(
    title="Face Recognition",
    description="Backend for Face Recognition App with Prisma and Milvus",
    version="0.3"
)

@app.get("/")
async def root():
    print("Root endpoint called")
    return {"message": "Face App Backend"}

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174"
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


@app.on_event("startup")
async def startup():
    """Initialize connections on startup."""
    # Try to connect to the database with retries
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
    
    # Connect to Milvus
    connect_to_milvus()
    global employee_collection, visitor_collection
    employee_collection = create_milvus_collection(EMPLOYEE_COLLECTION)
    visitor_collection = create_milvus_collection(VISITOR_COLLECTION)

@app.on_event("shutdown")
async def shutdown():
    """Clean up connections on shutdown."""
    await db.disconnect()
    if connections.has_connection("default"):
        connections.remove_connection("default")

# Milvus Configuration
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
EMPLOYEE_COLLECTION = "employee_embeddings"
VISITOR_COLLECTION = "visitor_embeddings"

MODEL_NAME = "VGG-Face"

# --- Utility Functions for Milvus ---
def connect_to_milvus():
    attempts = 5
    for attempt in range(attempts):
        try:
            # Remove existing connection if any
            if connections.has_connection("default"):
                connections.remove_connection("default")
            
            print(f"Attempting to connect to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
            connections.connect(
                alias="default",
                host=MILVUS_HOST,
                port=MILVUS_PORT,
                timeout=60  # Increased timeout
            )
            print(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
            return True
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    raise RuntimeError("Failed to connect to Milvus after several attempts")

def create_milvus_collection(collection_name):
    """Create a Milvus collection for embeddings."""
    try:
        if not utility.has_collection(collection_name):
            schema = CollectionSchema(
                fields=[
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=255),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=4096),
                ],
                description=f"{collection_name} for storing embeddings"
            )
            collection = Collection(name=collection_name, schema=schema)
            print(f"Created collection: {collection_name}")

            index_params = {
                "metric_type": "IP",
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
        else:
            collection = Collection(collection_name)
            collection.load()
        return collection
    except Exception as e:
        raise RuntimeError(f"Failed to create/load collection '{collection_name}': {str(e)}")

# --- Face Embedding Utilities ---
def preprocess_image(photo_bytes: bytes):
    """ Validate, resize, and normalize."""
    try:
        photo = Image.open(BytesIO(photo_bytes))
        if photo.mode != "RGB":
            photo = photo.convert("RGB")
        photo = photo.resize((224, 224))
        return np.array(photo)
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Invalid image uploaded.")

def extract_face_embedding(photo_bytes: bytes):
    """Extract face embedding using DeepFace."""
    try:
        photo_array = preprocess_image(photo_bytes)
        embedding = DeepFace.represent(
            img_path=photo_array, model_name=MODEL_NAME, enforce_detection=False
        )
        return embedding[0]["embedding"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting embedding: {str(e)}")

# --- utility function ---
def format_datetime(dt: datetime) -> str:

    ist = pytz.timezone('Asia/Kolkata')
    dt_ist = dt.astimezone(ist)
    return dt_ist.strftime("%B %d, %Y at %I:%M %p IST")

# function to detect the face
def search_in_milvus(collection_name, query_embedding, threshold=0.6):
    """Search for similar embeddings using cosine similarity."""
    try:
        # Normalize query embedding
        query_embedding = np.array(query_embedding)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        collection = Collection(collection_name)
        search_params = {
            "metric_type": "IP",  # Inner Product for cosine similarity
            "params": {"nprobe": 16}
        }
        
        results = collection.search(
            data=[query_embedding.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=1,
            output_fields=["name"]
        )
        
        if results and len(results[0]) > 0:
            
            match = results[0][0]
            similarity = float(match.distance)  # IP score is already cosine similarity
            
            if similarity >= threshold:
                return {
                    "name": match.entity.get("name"),
                    "similarity": similarity,
                    "match_found": True
                }
        return {"message": "No match found", "match_found": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during search: {str(e)}")
    

# --- Data Storage ---
async def save_to_prisma(name: str, age: int, gender: str, photo_base64: str, table: str):
    """Save user details in Prisma database."""
    if table == "employee":
        record = await db.employee.create(
            data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
        )
    elif table == "visitor":
        record = await db.visitor.create(
            data={"name": name, "age": age, "gender": gender, "photoBase64": photo_base64}
        )
    
    # Format the datetime fields
    return {
        **record.model_dump(),
        "createdAt": format_datetime(record.createdAt),
        "updatedAt": format_datetime(record.updatedAt)
    }

def save_to_milvus(collection_name, name, embedding):
    """Save normalized embeddings to Milvus."""
    collection = Collection(collection_name)
    # Normalize the embedding
    embedding = np.array(embedding)
    embedding = embedding / np.linalg.norm(embedding)
    data = [[name], [embedding.tolist()]]
    collection.insert(data)
    collection.flush()  # Ensure data is persisted

# --- Endpoints ---
@app.post("/register-employee/")
async def register_employee(
    name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None
):
    try:
        photo_bytes = await photo.read()
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        embedding = extract_face_embedding(photo_bytes)
        await save_to_prisma(name, age, gender, photo_base64, "employee")
        save_to_milvus(EMPLOYEE_COLLECTION, name, embedding)
        return {"message": "Employee registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

@app.post("/register-visitor/")
async def register_visitor(
    name: str = Form(...), age: int = Form(...), gender: str = Form(...), photo: UploadFile = None
):
    try:
        photo_bytes = await photo.read()
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        embedding = extract_face_embedding(photo_bytes)
        await save_to_prisma(name, age, gender, photo_base64, "visitor")
        save_to_milvus(VISITOR_COLLECTION, name, embedding)
        return {"message": "Visitor registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

@app.post("/recognize-employee/")
async def recognize_employee(photo: UploadFile):
    try:
        photo_bytes = await photo.read()
        query_embedding = extract_face_embedding(photo_bytes)
        collection = Collection(EMPLOYEE_COLLECTION)
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "IP", "params": {"nprobe": 10}},
            limit=1,
            output_fields=["name"]
        )
        if results and len(results[0]) > 0:
            match = results[0][0]
            return {"name": match.entity.get("name"), "similarity": float(match.distance)}
        return {"message": "No match found."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

@app.post("/recognize-visitor/")
async def recognize_visitor(photo: UploadFile):
    try:
        photo_bytes = await photo.read()
        query_embedding = extract_face_embedding(photo_bytes)
        collection = Collection(VISITOR_COLLECTION)
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "IP", "params": {"nprobe": 16}},
            limit=1,
            output_fields=["name"]
        )
        if results and len(results[0]) > 0:
            match = results[0][0]
            return {"name": match.entity.get("name"), "similarity": float(match.distance)}
        return {"message": "No match found."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")

# @app.post("/recognize-employee/")
# async def recognize_employee(photo: UploadFile):
#     try:
#         photo_bytes = await photo.read()
#         query_embedding = extract_face_embedding(photo_bytes)
#         result = search_in_milvus(EMPLOYEE_COLLECTION, query_embedding)
#         if result["match_found"]:
#             return {"name": result["name"], "similarity": result["similarity"]}
#         return {"message": result["message"]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")




# @app.post("/recognize-visitor/")
# async def recognize_visitor(photo: UploadFile):
#     try:
#         photo_bytes = await photo.read()
#         query_embedding = extract_face_embedding(photo_bytes)
#         result = search_in_milvus(VISITOR_COLLECTION, query_embedding)
#         if result["match_found"]:
#             return {"name": result["name"], "similarity": result["similarity"]}
#         return {"message": result["message"]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error in recognition: {str(e)}")




if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)



https://medium.com/@chnarsimha986/fastapi-login-logout-changepassword-4c12e92d41e2