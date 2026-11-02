import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

import database


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    """Use a throwaway SQLite database for every database and CLI test."""
    database_path = tmp_path / "students.sqlite3"
    engine = create_engine(
        URL.create("sqlite", database=str(database_path)),
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(database, "engine", engine)
    database.initialize_database()

    yield engine

    engine.dispose()
