from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from app.config import settings
from app.database import test_connection, close_db
from app.utils.logging import setup_logging
from app.utils.exceptions import DCEBaseException, format_error_response
from app.api import contracts, templates, validation

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Data Contract Engine...")
    
    try:
        test_connection()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Data Contract Engine...")
    close_db()
    logger.info("Database connections closed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DCEBaseException)
async def dce_exception_handler(request: Request, exc: DCEBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(exc, path=str(request.url))
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url)
        }
    )


app.include_router(contracts.router, prefix=settings.API_V1_PREFIX)
app.include_router(templates.router, prefix=settings.API_V1_PREFIX)
app.include_router(validation.router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check():
    try:
        test_connection()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc),
        "version": settings.VERSION
    }


@app.get("/")
async def root():
    return {
        "message": "Data Contract Engine API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }


@app.get(f"{settings.API_V1_PREFIX}/")
async def api_root():
    return {
        "message": "Data Contract Engine API v1",
        "version": settings.VERSION,
        "endpoints": {
            "contracts": f"{settings.API_V1_PREFIX}/contracts",
            "templates": f"{settings.API_V1_PREFIX}/contracts/templates",
            "health": "/health",
            "docs": "/docs"
        }
    }