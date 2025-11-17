import pytest
from sqlalchemy.orm import Session
from app.database import get_db, test_connection as db_test_connection, init_db 


def test_connection():
    result = db_test_connection()
    assert result is True


def test_database_connection():
    assert db_test_connection() is True  


def test_get_db_yields_session():
    db_gen = get_db()
    db = next(db_gen)
    assert isinstance(db, Session)

    try:
        next(db_gen)
    except StopIteration:
        pass


def test_init_db():
    init_db()


def test_test_db_fixture(test_db):
    assert test_db is not None
    assert isinstance(test_db, Session)