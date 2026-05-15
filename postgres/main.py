# main.py
import asyncio
import sys

from config import NUM_ORDER_WORKERS
from database import get_db_pool, init_db
from workers import order_worker
from importer import bulk_import_books

async def get_user_input(prompt_text: str) -> str:
    """
    Wraps the standard blocking input() function in a separate thread.
    This prevents the terminal prompt from freezing the asyncio background workers.
    """
    return await asyncio.to_thread(input, prompt_text)

# Update the interactive_terminal function in main.py
from inventory import add_stock  # Don't forget to import it at the top!

async def interactive_terminal(order_queue: asyncio.Queue, pool):
    """Handles the CLI interface for taking orders and restocking."""
    print("\n" + "="*40)
    print(" 🏪 INTERACTIVE BOOKSTORE TERMINAL")
    print("="*40)
    print("Available Commands:")
    print(" - Buy a book:  buy <book_id> <quantity>  (Example: buy 1 2)")
    print(" - Add stock:   add <book_id> <quantity>  (Example: add 1 50)")
    print(" - Quit:        q\n")
    
    order_counter = 1
    
    while True:
        try:
            user_input = await get_user_input("Enter command: ")
            parts = user_input.strip().lower().split()
            
            if not parts:
                continue
                
            command = parts[0]
            
            if command in ('q', 'quit', 'exit'):
                print("\nStopping interactive terminal...")
                break
                
            if len(parts) != 3:
                print("❌ Invalid format. Use: action book_id quantity (e.g., 'buy 1 2' or 'add 1 50').")
                continue
                
            book_id = int(parts[1])
            quantity = int(parts[2])
            
            if command == 'buy':
                print(f"🛒 Submitting Order #{order_counter}...")
                order_queue.put_nowait((book_id, quantity, order_counter))
                order_counter += 1
                
            elif command == 'add':
                # We can await this directly because restocking is usually an admin task, 
                # not a high-volume customer action that needs a queue.
                await add_stock(pool, book_id, quantity)
                
            else:
                print(f"❌ Unknown command: {command}")
            
            await asyncio.sleep(0.1) 
            
        except ValueError:
            print("❌ Invalid input. Book ID and Quantity must be numbers.")
        except Exception as e:
            print(f"❌ Error: {e}")

async def main():
    try:
        # 1. Initialize Database
        pool = await get_db_pool()
        await init_db(pool)
        print("Database connected and initialized.\n")
    except Exception as e:
        print(f"Could not connect to database. Error: {e}")
        return

    # 2. Spin up Async Order Processing System
    order_queue = asyncio.Queue()
    workers = [
        asyncio.create_task(order_worker(i, order_queue, pool)) 
        for i in range(NUM_ORDER_WORKERS)
    ]
    
    # 3. Start the Interactive Terminal
    # This will block the main function from progressing, but the background 
    # workers above are already running concurrently.
    await interactive_terminal(order_queue,pool=pool)
        
    # Wait for any remaining orders in the queue to be processed before moving on
    print("Waiting for pending orders to finish...")
    await order_queue.join() 
    
    # 4. Simulate Bulk Import with multiprocessing (runs after user quits terminal)
    mock_chunks = [[{"title": f"New Book {i}", "initial_stock": 50} for i in range(1000)] for _ in range(8)]
    await bulk_import_books(mock_chunks)
    
    # 5. Graceful Shutdown
    for w in workers:
        w.cancel()
    await pool.close()
    print("\nSystem shutdown complete.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())