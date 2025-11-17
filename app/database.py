import logging
from typing import Generator
from sqlalchemy import create_engine, event, text  
from sqlalchemy.orm import declarative_base  
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import Pool

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  
    pool_size=5,         
    max_overflow=15,     
    pool_timeout=30,     
    pool_recycle=3600,   
    echo=settings.DEBUG,  
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.debug("Database connection established")


@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug("Connection checked out from pool")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def close_db() -> None:
    logger.info("Closing database connections...")
    engine.dispose()
    logger.info("Database connections closed")


def test_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False