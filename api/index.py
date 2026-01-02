"""
Vercel Serverless API Entry Point
This file adapts the FastAPI app to work with Vercel's serverless functions
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import asyncpg

# Import your app components
from backend.app.config import get_settings
from backend.app.routers import market, stocks, shockers

settings = get_settings()

# Initialize FastAPI app (without lifespan for serverless)
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(market.router, prefix="/api")
app.include_router(stocks.router, prefix="/api")
app.include_router(shockers.router, prefix="/api")


@app.get("/")
@app.get("/api")
async def root():
    """API root endpoint"""
    return {
        "message": "MTF Market Intelligence API",
        "version": settings.API_VERSION,
        "status": "running",
        "docs": "/api/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            timeout=5
        )
        await conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "version": settings.API_VERSION
    }


# Mangum handler for Vercel
handler = Mangum(app, lifespan="off")
