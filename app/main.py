import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database.mongo import init_mongo_indexes
from app.api.auth import auth_router
from app.api.tasks import task_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(name)s  %(levelname)s  %(message)s")
logger = logging.getLogger("app.main")

app = FastAPI(title="Event Discovery Agent API", version="1.0.0")

# Startup lifecycle: connect to MongoDB and build indexes
@app.on_event("startup")
async def on_startup():
    logger.info("Initializing MongoDB connection and indexes...")
    await init_mongo_indexes()

# Mount API Routers
app.include_router(auth_router)
app.include_router(task_router)

# Mount Static Directory
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if not os.path.exists(static_dir):
    static_dir = "static"

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)

@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "mongodb"}
