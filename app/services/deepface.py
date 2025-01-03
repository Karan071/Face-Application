from deepface import DeepFace
import numpy as np
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException

MODEL_NAME = "VGG-Face"

def preprocess_image(photo_bytes: bytes):
    """Preprocess the uploaded photo."""
    try:
        photo = Image.open(BytesIO(photo_bytes))
        if photo.mode != "RGB":
            photo = photo.convert("RGB")
        photo = photo.resize((224, 224))
        return np.array(photo)
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Invalid image uploaded.")

def extract_face_embedding(photo_bytes: bytes):
    """Extract face embeddings using DeepFace."""
    try:
        photo_array = preprocess_image(photo_bytes)
        embedding = DeepFace.represent(
            img_path=photo_array, model_name=MODEL_NAME, enforce_detection=False
        )
        return embedding[0]["embedding"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting embedding: {str(e)}")
