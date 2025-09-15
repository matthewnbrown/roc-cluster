"""
Database configuration and session management
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
import os
from typing import Generator
from config import settings

# Database configuration
DATABASE_URL = settings.DATABASE_URL

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_size=settings.DB_POOL_SIZE,  # Number of connections to maintain in the pool
    max_overflow=settings.DB_MAX_OVERFLOW,  # Additional connections that can be created on demand
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=settings.DB_POOL_RECYCLE,  # Recycle connections after specified time
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
