"""Async Postgres connection pool (asyncpg), shared across the app."""
import os
import asyncpg
from pgvector.asyncpg import register_vector

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
        dsn=os.environ["DATABASE_URL"],
        min_size=1,
        max_size=10,
        # Supabase's transaction-mode PgBouncer cannot safely reuse asyncpg's
        # named prepared statements across client connections.
        statement_cache_size=0,
        init=_init_connection,
        )
    return _pool


async def _init_connection(conn: asyncpg.Connection) -> None:
    # register pgvector codec so we can pass/receive Python lists as vector columns
    await register_vector(conn)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Pool not initialized — call init_pool() first (e.g. in FastAPI startup)")
    return _pool
