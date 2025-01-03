from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymilvus import connections
from app.api import employee, visitor
from app.core.config import settings
from app.core.db import db, initialize_db
from app.services.milvus import connect_to_milvus, create_milvus_collection

app = FastAPI(
    title="Face Recognition",
    description="Backend for Face Recognition App with Prisma and Milvus",
    version="0.3"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(employee.router)
app.include_router(visitor.router)

@app.on_event("startup")
async def startup():
    await initialize_db()
    connect_to_milvus()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()
    if connections.has_connection("default"):
        connections.remove_connection("default")
