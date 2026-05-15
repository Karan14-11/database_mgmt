# inventory.py
import aiosqlite

async def process_single_order(conn: aiosqlite.Connection, book_id: int, quantity: int, order_id: int) -> bool:
    """Handles order processing safely for SQLite."""
    # Step 1: Check current stock
    async with conn.execute('SELECT stock_level FROM inventory WHERE book_id = ?', (book_id,)) as cursor:
        row = await cursor.fetchone()

    if not row:
        print(f"Order {order_id}: Book {book_id} not found.")
        return False

    current_stock = row[0] # aiosqlite returns tuples by default

    if current_stock >= quantity:
        # Step 2: Atomic update. 
        # We re-verify stock_level >= quantity in the query to prevent race conditions!
        async with conn.execute('''
            UPDATE inventory 
            SET stock_level = stock_level - ? 
            WHERE book_id = ? AND stock_level >= ?
        ''', (quantity, book_id, quantity)) as cursor:
            
            if cursor.rowcount > 0:
                await conn.commit()
                print(f"[SUCCESS] Order {order_id}: Bought {quantity}. Stock remaining: {current_stock - quantity}")
                return True
            else:
                # Another worker beat us to the update and dropped the stock below required
                print(f"[FAILED]  Order {order_id}: Out of stock due to simultaneous purchase.")
                return False
    else:
        print(f"[FAILED]  Order {order_id}: Out of stock (Requested: {quantity}, Available: {current_stock})")
        return False

async def add_stock(conn: aiosqlite.Connection, book_id: int, quantity_to_add: int) -> bool:
    """Safely adds new stock to an existing book."""
    if quantity_to_add <= 0:
        return False

    # Atomic addition
    async with conn.execute('''
        UPDATE inventory SET stock_level = stock_level + ? WHERE book_id = ?
    ''', (quantity_to_add, book_id)) as cursor:
        if cursor.rowcount > 0:
            await conn.commit()
            print(f"📦 [RESTOCK SUCCESS] Book {book_id} received {quantity_to_add} new copies.")
            return True
        else:
            print(f"❌ [RESTOCK FAILED] Book {book_id} not found.")
            return False

async def add_book(conn: aiosqlite.Connection, book_id: int, book_title:str,book_qty:int=0)-> bool:
    """Adds a new book to the inventory with initial stock of 0."""
    try:
        await conn.execute('INSERT INTO books (book_id, title) VALUES (?, ?)', (book_id, book_title))
        await conn.execute('INSERT INTO inventory (book_id, stock_level) VALUES (?, ?)', (book_id,book_qty))
        await conn.commit()
        print(f"📚 [BOOK ADDED] '{book_title}' with ID {book_id} added to inventory.")
        return True
    except aiosqlite.IntegrityError:
        print(f"❌ [ADD BOOK FAILED] Book ID {book_id} already exists.")
        return False