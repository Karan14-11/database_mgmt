# database.py
import asyncpg
from config import DATABASE_URI

async def get_db_pool() -> asyncpg.Pool:
    """Creates and returns an asyncpg database connection pool."""
    return await asyncpg.create_pool(DATABASE_URI)

async def init_db(pool: asyncpg.Pool):
    """Initializes the database schemas and seeds test data."""
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS books (
                book_id SERIAL PRIMARY KEY,
                title TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS inventory (
                book_id INTEGER REFERENCES books(book_id),
                stock_level INTEGER NOT NULL CHECK (stock_level >= 0)
            );
        ''')
        # Seed test data
        await conn.execute(
            'INSERT INTO books (book_id, title) VALUES (1, $1) ON CONFLICT DO NOTHING', 
            'System Design Interview Guide'
        )
        await conn.execute(
            'INSERT INTO inventory (book_id, stock_level) VALUES (1, 10) ON CONFLICT DO NOTHING'
        )