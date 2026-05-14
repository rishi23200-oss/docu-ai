from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

client: AsyncIOMotorClient = None


async def connect_to_mongo():
    global client
    logger.info("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    logger.info("Connected to MongoDB")


async def close_mongo_connection():
    global client
    if client:
        logger.info("Closing MongoDB connection...")
        client.close()


async def get_database() -> AsyncIOMotorDatabase:
    return client[settings.MONGODB_DB_NAME]


async def get_collection(collection_name: str):
    db = await get_database()
    return db[collection_name]
