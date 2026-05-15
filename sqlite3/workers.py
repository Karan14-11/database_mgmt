# workers.py
import asyncio
import aiosqlite
from inventory import process_single_order

async def order_worker(worker_id: int, queue: asyncio.Queue, conn: aiosqlite.Connection):
    """Background worker that continuously processes orders from the async queue."""
    while True:
        try:
            # Safely wait for an item outside the try/finally block
            order = await queue.get()
        except asyncio.CancelledError:
            break 
            
        try:
            book_id, quantity, order_id = order
            await process_single_order(conn, book_id, quantity, order_id)
        except Exception as e:
            print(f"Worker {worker_id} encountered an error: {e}")
        finally:
            queue.task_done()