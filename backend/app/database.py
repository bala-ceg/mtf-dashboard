import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from .config import get_settings

settings = get_settings()

# Global connection pool
_pool: asyncpg.Pool | None = None


async def init_db_pool():
    """Initialize database connection pool"""
    global _pool
    _pool = await asyncpg.create_pool(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        min_size=2,
        max_size=10,
        command_timeout=60
    )
    print(f"✅ Database pool initialized: {settings.DB_NAME}")


async def close_db_pool():
    """Close database connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        print("🔌 Database pool closed")


@asynccontextmanager
async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get database connection from pool"""
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    
    async with _pool.acquire() as connection:
        yield connection


async def execute_query(query: str, params: tuple = None) -> list[dict]:
    """Execute SQL query and return results as list of dicts"""
    async with get_db() as conn:
        if params:
            rows = await conn.fetch(query, *params)
        else:
            rows = await conn.fetch(query)
        return [dict(row) for row in rows]


async def execute_query_one(query: str) -> dict | None:
    """Execute SQL query and return single result as dict"""
    async with get_db() as conn:
        row = await conn.fetchrow(query)
        return dict(row) if row else None
