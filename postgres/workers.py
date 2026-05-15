# workers.py
import asyncio
import asyncpg
from inventory import process_single_order

async def order_worker(worker_id: int, queue: asyncio.Queue, pool: asyncpg.Pool):
    """Background worker that continuously processes orders from the async queue."""
    while True:
        try:
            # Wait for an order to be placed in the queue
            order = await queue.get()
        except asyncio.CancelledError:
            print(f"Worker {worker_id} is shutting down...")
            break
        try:
            book_id, quantity, order_id = order
            
            # Process the database transaction
            await process_single_order(pool, book_id, quantity, order_id)
        except Exception as e:
            print(f"Worker {worker_id} encountered an error: {e}")
        finally:
            # Always notify the queue that the task is finished
            queue.task_done()