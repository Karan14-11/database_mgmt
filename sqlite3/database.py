# database.py
import aiosqlite
from config import DATABASE_URI

async def get_db_connection():
    """Returns a single aiosqlite connection (SQLite handles concurrency via file locks)."""
    return await aiosqlite.connect(DATABASE_URI)

async def init_db(conn: aiosqlite.Connection):
    """Initializes the SQLite schema."""
    # SQLite uses INTEGER PRIMARY KEY AUTOINCREMENT instead of SERIAL
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS books (
            book_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL
        );
    ''')
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            book_id INTEGER REFERENCES books(book_id),
            stock_level INTEGER NOT NULL CHECK (stock_level >= 0)
        );
    ''')
    
    # Insert dummy data (SQLite uses 'IGNORE' instead of 'DO NOTHING')
    await conn.execute("INSERT OR IGNORE INTO books (book_id, title) VALUES (1, 'System Design Interview Guide')")
    
    # Ensure starting stock is 10 for our test
    await conn.execute("DELETE FROM inventory WHERE book_id = 1")
    await conn.execute("INSERT INTO inventory (book_id, stock_level) VALUES (1, 10)")
    
    await conn.commit()