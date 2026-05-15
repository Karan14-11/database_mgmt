# inventory.py
import asyncpg

async def process_single_order(pool: asyncpg.Pool, book_id: int, quantity: int, order_id: int) -> bool:
    """Handles order processing safely using row-level database locking."""
    async with pool.acquire() as conn:
        # Begin Transaction
        async with conn.transaction():
            # FOR UPDATE locks the row, preventing race conditions
            row = await conn.fetchrow(
                'SELECT stock_level FROM inventory WHERE book_id = $1 FOR UPDATE', 
                book_id
            )

            if not row:
                print(f"Order {order_id}: Book {book_id} not found.")
                return False

            current_stock = row['stock_level']

            if current_stock >= quantity:
                new_stock = current_stock - quantity
                await conn.execute(
                    'UPDATE inventory SET stock_level = $1 WHERE book_id = $2',
                    new_stock, book_id
                )
                print(f"[SUCCESS] Order {order_id}: Bought {quantity}. Stock remaining: {new_stock}")
                return True
            else:
                print(f"[FAILED]  Order {order_id}: Out of stock (Requested: {quantity}, Available: {current_stock})")
                return False
            
# Add this to the bottom of inventory.py

async def add_stock(pool, book_id: int, quantity_to_add: int) -> bool:
    """Safely adds new stock to an existing book."""
    if quantity_to_add <= 0:
        print("❌ Quantity to add must be greater than zero.")
        return False

    async with pool.acquire() as conn:
        # The database does the math for us safely, avoiding race conditions
        new_stock = await conn.fetchval('''
            UPDATE inventory 
            SET stock_level = stock_level + $1 
            WHERE book_id = $2
            RETURNING stock_level
        ''', quantity_to_add, book_id)

        if new_stock is not None:
            print(f"📦 [RESTOCK SUCCESS] Book {book_id} received {quantity_to_add} new copies. Total stock is now: {new_stock}")
            return True
        else:
            print(f"❌ [RESTOCK FAILED] Book {book_id} not found in inventory.")
            return False