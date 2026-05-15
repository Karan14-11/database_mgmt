# importer.py
import asyncio
import concurrent.futures
import time

def parse_and_format_chunk(chunk: list) -> list:
    """
    Simulates CPU-bound work (e.g., parsing a massive CSV).
    This runs in a separate process entirely.
    """
    processed_data = []
    for item in chunk:
        # Simulate heavy CPU computation
        _ = [i * i for i in range(2000)]
        processed_data.append((item['title'], item['initial_stock']))
    return processed_data

async def bulk_import_books(raw_chunks: list):
    """Uses a ProcessPoolExecutor to handle bulk imports across CPU cores."""
    loop = asyncio.get_running_loop()
    
    print("\n--- Starting Parallel Bulk Import ---")
    start_time = time.time()
    
    with concurrent.futures.ProcessPoolExecutor() as process_pool:
        # Pass chunks to different CPU cores
        tasks = [
            loop.run_in_executor(process_pool, parse_and_format_chunk, chunk)
            for chunk in raw_chunks
        ]
        
        # Wait for all processes to return their parsed data
        results = await asyncio.gather(*tasks)
        
    print(f"Parallel Parsing completed in {time.time() - start_time:.2f} seconds.")
    print(f"Total chunks processed: {len(results)}")
    
    return results