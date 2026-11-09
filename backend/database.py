"""Database models and connection for CodeDNA.

SQLite database storing repository metadata, commit records,
extracted features, anomaly flags, AI-code classification results,
and authentication data.
"""

import os
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, Text, Boolean, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

# Module-level engine singleton — created once, reused across sessions
_engine = None


def get_engine(db_path: str = None):
    """Create and return a SQLAlchemy engine (singleton)."""
    global _engine
    if _engine is None:
        if db_path is None:
            db_path = os.getenv("CODEDNA_DB", "sqlite:///codedna.db")
        _engine = create_engine(db_path, echo=False, pool_pre_ping=True)
    return _engine


def init_db(db_path: str = None):
    """Initialise the database, creating all tables."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


def get_session(db_path: str = None):
    """Return a new database session (reuses singleton engine)."""
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()


class User(Base):
    """User accounts for API authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), nullable=False, unique=True, index=True)
    api_key_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # "admin" or "user"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    repositories = relationship("Repository", back_populates="owner_user", cascade="all, delete-orphan")
    session_tokens = relationship("SessionToken", back_populates="user", cascade="all, delete-orphan")


class Repository(Base):
    """Tracked GitHub repositories."""
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_name = Column(String(255), nullable=False)
    owner = Column(String(255), nullable=False)
    description = Column(Text)
    language = Column(String(100))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_collected = Column(DateTime, nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("owner", "repo_name", name="uq_owner_repo_name"),
    )

    owner_user = relationship("User", back_populates="repositories")
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")
    features = relationship("Feature", back_populates="repository", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="repository", cascade="all, delete-orphan")


class Commit(Base):
    """Individual commit records fetched from GitHub API."""
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    sha = Column(String(100), nullable=False)
    author_name = Column(String(255))
    author_email = Column(String(255))
    commit_date = Column(DateTime, nullable=False)
    message = Column(Text)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    total_changes = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("repo_id", "sha", name="uq_repo_id_sha"),
    )

    repository = relationship("Repository", back_populates="commits")


class Feature(Base):
    """Extracted behavioural features per repository."""
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    commits_per_day = Column(Float, default=0.0)
    active_days = Column(Integer, default=0)
    weekend_activity = Column(Integer, default=0)
    avg_commits_per_week = Column(Float, default=0.0)
    time_of_day_distribution = Column(Text)  # JSON string
    avg_gap_between_commits_hours = Column(Float, default=0.0)
    code_change_volume = Column(Integer, default=0)
    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    repository = relationship("Repository", back_populates="features")


class Anomaly(Base):
    """Anomaly flags from Isolation Forest."""
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    anomaly_score = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, default=False)
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    repository = relationship("Repository", back_populates="anomalies")


class ClassificationResult(Base):
    """AI vs human code classification results."""
    __tablename__ = "classification_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    file_path = Column(String(500))
    is_ai_generated = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    model_version = Column(String(100))
    classified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    repository = relationship("Repository")


class APIToken(Base):
    """API tokens for authentication."""
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    role = Column(String(20), nullable=False, default="user")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)


class SessionToken(Base):
    """Session tokens for authenticated user sessions."""
    __tablename__ = "session_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="session_tokens")