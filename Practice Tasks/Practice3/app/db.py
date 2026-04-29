import asyncpg


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(dsn, min_size=5, max_size=30)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                key  TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
    return pool


async def db_get(pool: asyncpg.Pool, key: str) -> str | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT value FROM items WHERE key = $1", key)
        return row["value"] if row else None


async def db_set(pool: asyncpg.Pool, key: str, value: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO items (key, value) VALUES ($1, $2) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            key, value,
        )


async def db_clear(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE items")
