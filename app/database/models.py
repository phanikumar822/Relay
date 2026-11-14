import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey, Text
from app.database.session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserTask(Base):
    __tablename__ = "user_tasks"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    raw_prompt = Column(Text, nullable=False)
    status = Column(String(50), default="QUEUED")
    email_dispatched = Column(Boolean, default=False)
    result_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ScrapedEvent(Base):
    __tablename__ = "scraped_events"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_url = Column(String(512), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    platform = Column(String(100), nullable=True)
    event_date = Column(String(100), nullable=True)
    priority = Column(String(20), nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
