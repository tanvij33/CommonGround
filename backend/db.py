"""Database configuration and SQLAlchemy models for Common Ground.

Stores trips, user profiles, generated trip plans, and cached Qloo responses
in a local SQLite database located at `data/common_ground.db`.
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Resolve database URL (defaults to SQLite in the project data/ directory)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/common_ground.db")

# Ensure the parent directory for the SQLite database file exists
if DATABASE_URL.startswith("sqlite:///"):
    db_relative_path = DATABASE_URL.replace("sqlite:///", "")
    db_file_path = Path(db_relative_path)
    db_file_path.parent.mkdir(parents=True, exist_ok=True)

# Create engine
# check_same_thread=False is needed for SQLite when accessed across multiple threads
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base model for SQLAlchemy ORM
Base = declarative_base()


class TripDB(Base):
    """SQLAlchemy model for group trips."""
    __tablename__ = "trips"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    name = Column(String, nullable=True)
    destination = Column(String, nullable=False, index=True)
    destination_query = Column(String, nullable=True)  # Precise Qloo location string used for venue lookups
    days = Column(Integer, default=2)
    status = Column(String, default="waiting")  # waiting, running, done, failed
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    profiles = relationship("ProfileDB", back_populates="trip", cascade="all, delete-orphan")
    plans = relationship("PlanDB", back_populates="trip", cascade="all, delete-orphan")


class ProfileDB(Base):
    """SQLAlchemy model for traveler profiles belonging to a trip."""
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    favorites_json = Column(Text, default="[]")       # JSON array of cultural favorites
    constraints_json = Column(Text, default="{}")     # JSON object of constraints

    trip = relationship("TripDB", back_populates="profiles")

    @property
    def favorites(self):
        try:
            return json.loads(self.favorites_json or "[]")
        except Exception:
            return []

    @favorites.setter
    def favorites(self, value):
        self.favorites_json = json.dumps(value)

    @property
    def constraints(self):
        try:
            return json.loads(self.constraints_json or "{}")
        except Exception:
            return {}

    @constraints.setter
    def constraints(self, value):
        self.constraints_json = json.dumps(value)


class PlanDB(Base):
    """SQLAlchemy model for stored itineraries and fairness evaluations."""
    __tablename__ = "plans"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False, index=True)
    destination = Column(String, nullable=False)
    title = Column(String, default="Balanced Group Itinerary")
    fairness_score = Column(Float, default=0.0)
    plan_json = Column(Text, nullable=False)           # Full JSON payload of the Plan model
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    trip = relationship("TripDB", back_populates="plans")


class QlooCacheDB(Base):
    """SQLAlchemy model to cache Qloo API responses in SQLite to prevent duplicate calls."""
    __tablename__ = "qloo_cache"

    cache_key = Column(String, primary_key=True, index=True) # Hash of endpoint + params
    endpoint = Column(String, nullable=False)
    request_params = Column(Text, default="{}")
    response_body = Column(Text, nullable=False)            # Stored JSON string
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    """Initializes all database tables defined above and ensures schema updates."""
    Base.metadata.create_all(bind=engine)
    if DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            for col_name, col_def in [
                ("name", "TEXT"),
                ("days", "INTEGER DEFAULT 2"),
                ("status", "TEXT DEFAULT 'waiting'"),
                ("destination_query", "TEXT")
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE trips ADD COLUMN {col_name} {col_def}"))
                    conn.commit()
                except Exception:
                    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency helper to yield an isolated database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

