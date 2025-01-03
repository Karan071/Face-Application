from prisma import Prisma
from app.core.config import settings
import asyncio

db = Prisma()

async def initialize_db():
    """Initialize Prisma client and connect to the database."""
    await db.connect()
    print("Connected to PostgreSQL database")
