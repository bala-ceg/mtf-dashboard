from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import get_settings
from .database import init_db_pool, close_db_pool
from .routers import market, stocks, shockers, indices

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    await init_db_pool()
    yield
    # Shutdown
    await close_db_pool()


# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development/testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(market.router, prefix=settings.API_PREFIX)
app.include_router(stocks.router, prefix=settings.API_PREFIX)
app.include_router(shockers.router, prefix=settings.API_PREFIX)
app.include_router(indices.router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "MTF Market Intelligence API",
        "version": settings.API_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
