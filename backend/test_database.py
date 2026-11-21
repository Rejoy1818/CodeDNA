"""Tests for the database module using an in-memory SQLite database."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect

from database import Base, get_engine, get_session, init_db, Repository, Commit


@pytest.fixture
def engine():
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    Session = __import__("sqlalchemy.orm", fromlist=["sessionmaker"]).sessionmaker(bind=engine)
    return Session()


def test_init_db_creates_tables(engine):
    table_names = inspect(engine).get_table_names()
    assert "repositories" in table_names
    assert "commits" in table_names


def test_create_repository_and_commit(session):
    repo = Repository(
        repo_name="test-repo-1",
        owner="test-owner",
        description="A library",
        language="JavaScript",
    )
    session.add(repo)
    session.flush()

    commit = Commit(
        repo_id=repo.id,
        sha="abc123",
        author_name="Alice",
        author_email="alice@x.com",
        commit_date=datetime.now(timezone.utc),
        message="Fix bug",
        additions=10,
        deletions=5,
        total_changes=15,
    )
    session.add(commit)
    session.commit()

    saved_repo = session.query(Repository).filter_by(repo_name="test-repo-1").first()
    assert saved_repo is not None
    assert saved_repo.owner == "test-owner"
    assert len(saved_repo.commits) == 1
    assert saved_repo.commits[0].sha == "abc123"


def test_unique_constraint_owner_repo(session):
    repo1 = Repository(repo_name="test-repo-2", owner="test-owner")
    repo2 = Repository(repo_name="test-repo-2", owner="test-owner")
    session.add(repo1)
    session.flush()
    session.add(repo2)
    with pytest.raises(Exception):
        session.commit()


def test_repository_relationships(session):
    repo = Repository(repo_name="test-repo-3", owner="owner")
    session.add(repo)
    session.flush()

    Feature = __import__("database", fromlist=["Feature"]).Feature
    feature = Feature(
        repo_id=repo.id,
        commits_per_day=1.5,
        active_days=5,
        weekend_activity=1,
        avg_commits_per_week=10.0,
        time_of_day_distribution="{}",
        avg_gap_between_commits_hours=24.0,
        code_change_volume=100,
    )
    session.add(feature)
    session.commit()

    saved = session.query(Repository).filter_by(repo_name="test-repo-3").first()
    assert len(saved.features) == 1
    assert saved.features[0].commits_per_day == 1.5
