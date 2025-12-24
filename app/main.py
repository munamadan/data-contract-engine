from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from app.api import versions, metrics
import logging
from app.config import settings
from app.database import test_connection, close_db, init_db
from app.utils.logging import setup_logging
from app.utils.exceptions import DCEBaseException, format_error_response
from app.utils.scheduler import setup_scheduler
from app.api import contracts, templates, validation

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Data Contract Engine...")
    
    try:
        test_connection()
        logger.info("Database connection successful")
        
        init_db()
        logger.info("Database initialized")
        
        setup_scheduler()
        logger.info("Scheduler setup complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Data Contract Engine...")
    
    try:
        close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Data Contract Engine API for managing and validating data contracts",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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
app.include_router(versions.router, prefix=settings.API_V1_PREFIX)
app.include_router(metrics.router, prefix=settings.API_V1_PREFIX)

@app.get("/health")
async def health_check():
    try:
        test_connection()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Health check database error: {e}")
        db_status = "disconnected"
    
    overall_status = "healthy" if db_status == "connected" else "unhealthy"
    
    return {
        "status": overall_status,
        "database": db_status,
        "timestamp": datetime.now(timezone.utc),
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME
    }

@app.get("/")
async def root():
    return {
        "message": "Data Contract Engine API",
        "version": settings.VERSION,
        "description": "API for managing and validating data contracts",
        "docs": "/docs",
        "health": "/health",
        "api_version": "v1",
        "api_prefix": settings.API_V1_PREFIX
    }

@app.get(f"{settings.API_V1_PREFIX}/")
async def api_root():
    return {
        "message": "Data Contract Engine API v1",
        "version": settings.VERSION,
        "endpoints": {
            "contracts": f"{settings.API_V1_PREFIX}/contracts",
            "templates": f"{settings.API_V1_PREFIX}/contracts/templates",
            "validation": f"{settings.API_V1_PREFIX}/validate",
            "versions": f"{settings.API_V1_PREFIX}/contracts/{{id}}/versions",
            "metrics": f"{settings.API_V1_PREFIX}/metrics",
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }

@app.on_event("startup")
async def startup_event():
    logger.warning("Using deprecated @app.on_event('startup') - use lifespan context manager instead")

@app.on_event("shutdown")
async def shutdown_event():
    logger.warning("Using deprecated @app.on_event('shutdown') - use lifespan context manager instead")