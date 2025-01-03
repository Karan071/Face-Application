import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
    EMPLOYEE_COLLECTION = "employee_embeddings"
    VISITOR_COLLECTION = "visitor_embeddings"
    MODEL_NAME = "VGG-Face"
    CORS_ORIGINS = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ]

settings = Settings()
