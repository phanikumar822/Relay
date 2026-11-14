import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logger = logging.getLogger("agent.mongo")

_client = None
_db = None
is_mock = False

async def get_or_init_db():
    global _client, _db, is_mock
    if _db is not None:
        return _db
    
    try:
        # Try connecting to live MongoDB (local or Atlas)
        real_client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=1500)
        await real_client.admin.command("ping")
        _client = real_client
        _db = _client[settings.MONGODB_DB_NAME]
        is_mock = False
        logger.info("Connected to LIVE MongoDB at %s (Database: %s)", settings.MONGODB_URL, settings.MONGODB_DB_NAME)
    except Exception as e:
        logger.warning(
            "Live MongoDB not reachable at %s (%s). Using Async MongoMock so login & dashboard work seamlessly.",
            settings.MONGODB_URL, e
        )
        from mongomock_motor import AsyncMongoMockClient
        _client = AsyncMongoMockClient()
        _db = _client[settings.MONGODB_DB_NAME]
        is_mock = True
        logger.info("Async MongoMock database initialized.")

    return _db

def get_mongo_db():
    global _db, _client
    if _db is None:
        # For synchronous access before async startup, return initialized client or mock
        from mongomock_motor import AsyncMongoMockClient
        _client = AsyncMongoMockClient()
        _db = _client[settings.MONGODB_DB_NAME]
    return _db

def users_col():
    return get_mongo_db()["users"]

def tasks_col():
    return get_mongo_db()["user_tasks"]

def events_col():
    return get_mongo_db()["scraped_events"]

class MongoUser:
    def __init__(self, doc: dict):
        self._doc = doc or {}
        self.id = str(self._doc.get("_id", ""))
        self.email = self._doc.get("email", "")
        self.created_at = self._doc.get("created_at")

    def __getitem__(self, item):
        if item == "id":
            return self.id
        return self._doc.get(item)

    def get(self, key, default=None):
        if key == "id":
            return self.id
        return self._doc.get(key, default)

async def ping_mongo() -> bool:
    try:
        db = await get_or_init_db()
        return not is_mock
    except Exception:
        return False

async def init_mongo_indexes():
    try:
        db = await get_or_init_db()
        users = db["users"]
        await users.create_index("email", unique=True)
        
        tasks = db["user_tasks"]
        await tasks.create_index("user_id")
        await tasks.create_index("created_at")
        
        events = db["scraped_events"]
        await events.create_index("event_url", unique=True)
        logger.info("MongoDB indexes verified.")
    except Exception as e:
        logger.warning("Index setup notice: %s", e)
