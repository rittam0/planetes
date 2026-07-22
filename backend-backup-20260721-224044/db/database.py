"""Database setup for AstraScope."""
import os
from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import redis

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://astra:astra@db:5432/astrascope")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


class OrbitalObjectDB(Base):
    __tablename__ = "orbital_objects"

    norad_id = Column(String(20), primary_key=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)
    tle_line1 = Column(Text, nullable=False)
    tle_line2 = Column(Text, nullable=False)
    epoch = Column(DateTime, nullable=False)
    inclination_deg = Column(Float, nullable=False)
    eccentricity = Column(Float, nullable=False)
    mean_motion = Column(Float, nullable=False)
    period_min = Column(Float, nullable=False)
    apogee_km = Column(Float, nullable=False)
    perigee_km = Column(Float, nullable=False)
    altitude_km = Column(Float, nullable=False)
    velocity_kms = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    data_source = Column(String(50), default="celestrak")
    updated_at = Column(DateTime, default=datetime.utcnow)


class ConjunctionEventDB(Base):
    __tablename__ = "conjunction_events"

    id = Column(String(100), primary_key=True)
    primary_norad = Column(String(20), nullable=False)
    primary_name = Column(String(200), nullable=False)
    secondary_norad = Column(String(20), nullable=False)
    secondary_name = Column(String(200), nullable=False)
    tca = Column(DateTime, nullable=False)
    max_probability = Column(Float, nullable=False)
    min_range_km = Column(Float, nullable=False)
    relative_velocity_kms = Column(Float, nullable=False)
    data_source = Column(String(50), default="celestrak_socrates")
    updated_at = Column(DateTime, default=datetime.utcnow)


class IngestionLogDB(Base):
    __tablename__ = "ingestion_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # success | failure | partial
    objects_ingested = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_cached(key: str, ttl: int = 3600) -> Optional[str]:
    """Get from Redis cache."""
    return redis_client.get(key)


def set_cached(key: str, value: str, ttl: int = 3600):
    """Set in Redis cache."""
    redis_client.setex(key, ttl, value)
