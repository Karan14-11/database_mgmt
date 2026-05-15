# main.py
import asyncio
import sys

from config import NUM_ORDER_WORKERS
from database import get_db_connection, init_db
from workers import order_worker
from importer import bulk_import_books
from inventory import add_stock, add_book

async def get_user_input(prompt_text: str) -> str:
    return await asyncio.to_thread(input, prompt_text)

async def interactive_terminal(order_queue: asyncio.Queue, conn):
    print("\n" + "="*40)
    print(" 🏪 INTERACTIVE BOOKSTORE TERMINAL (SQLite Version)")
    print("="*40)
    print(" - Buy a book:  buy <book_id> <quantity>  (Example: buy 1 2)")
    print(" - Add stock:   add <book_id> <quantity>  (Example: add 1 50)")
    print(" - Quit:        q\n")
    
    order_counter = 1
    while True:
        try:
            user_input = await get_user_input("Enter command: ")
            parts = user_input.strip().lower().split()
            
            if not parts: continue
            command = parts[0]
            
            if command in ('q', 'quit', 'exit'):
                print("\nStopping interactive terminal...")
                break
                
            if not(len(parts) == 3 or (command == 'add_book' and len(parts) == 4)):
                print("❌ Invalid format.")
                continue
                
            book_id, quantity = int(parts[1]), int(parts[2]),
            
            if command == 'buy':
                print(f"🛒 Submitting Order #{order_counter}...")
                order_queue.put_nowait((book_id, quantity, order_counter))
                order_counter += 1
            elif command == 'add':
                await add_stock(conn, book_id, quantity)
            elif command =='add_book':
                book_title= parts[3]
                await add_book(conn, book_id,book_title, quantity)
            else:
                print(f"❌ Unknown command: {command}")
            
            await asyncio.sleep(0.1) 
            
        except Exception as e:
            print(f"❌ Error: {e}")

async def main():
    try:
        # SQLite Connection (Single shared connection for all workers)
        conn = await get_db_connection()
        await init_db(conn)
        print("SQLite Database 'bookstore.db' connected and initialized.\n")
    except Exception as e:
        print(f"Could not connect to database. Error: {e}")
        return

    order_queue = asyncio.Queue()
    workers = [
        asyncio.create_task(order_worker(i, order_queue, conn)) 
        for i in range(NUM_ORDER_WORKERS)
    ]
    
    await interactive_terminal(order_queue, conn)
        
    print("Waiting for pending orders to finish...")
    await order_queue.join() 
    
    mock_chunks = [[{"title": f"New Book {i}", "initial_stock": 50} for i in range(1000)] for _ in range(8)]
    await bulk_import_books(mock_chunks)
    
    for w in workers:
        w.cancel()
    await conn.close()
    print("\nSystem shutdown complete.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())