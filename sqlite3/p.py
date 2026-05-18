import asyncio
import os
from concurrent.futures import ProcessPoolExecutor
from cengine import get_ptd
from h import (
    alpha_a1_token_book, 
    alpha_a2_flow_risk,
    beta_b1_tick_summary,
    beta_b2_member_fees,
    consolidated_c1_report
)
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class ETLPipeline:
    def __init__(self, ctd: str, data_dir: str = "data", out_dir: str = "output"):
        self.ctd = ctd
        self.ptd = get_ptd(ctd)
        self.data_dir = data_dir
        self.out_dir = out_dir
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.out_dir, exist_ok=True)

    def _path(self, exchange: str, file_type: str, date_str: str) -> str:
        return os.path.join(self.data_dir, f"{exchange}_{file_type}_{date_str}.csv")

    def _out_path(self, filename: str) -> str:
        return os.path.join(self.out_dir, f"{filename}_{self.ctd}.csv")

    async def run(self):
        logging.info(f"=== Starting Asynchronous DAG Pipeline ===")
        logging.info(f"CTD: {self.ctd} | PTD: {self.ptd}")
        
        loop = asyncio.get_running_loop()
        
        # Output Paths
        a1_out = self._out_path("alpha_token_book")
        a2_out = self._out_path("alpha_flow_risk")
        b1_out = self._out_path("beta_tick_summary")
        b2_out = self._out_path("beta_member_fees")
        c1_out = self._out_path("consolidated_cross_report")

        with ProcessPoolExecutor() as pool:
            
            # ---------------------------------------------------------
            # 1. FIRE INDEPENDENT TASKS IMMEDIATELY
            # These return asyncio.Future objects representing the running process.
            # Notice we do NOT `await` them here, allowing the loop to continue reading code.
            # ---------------------------------------------------------
            logging.info("Firing base tasks (A1, B1, B2)...")
            
            task_a1 = loop.run_in_executor(
                pool, alpha_a1_token_book, 
                self._path('alpha', 'ref', self.ctd), self._path('alpha', 'settle', self.ptd), a1_out
            )
            
            task_b1 = loop.run_in_executor(
                pool, beta_b1_tick_summary,
                self._path('beta', 'ticks', self.ctd), b1_out
            )
            
            # Since B2 relies only on raw files (ticks, members, policy), 
            # it is actually independent! It doesn't need to wait for B1.
            task_b2 = loop.run_in_executor(
                pool, beta_b2_member_fees,
                self._path('beta', 'ticks', self.ctd), self._path('beta', 'members', self.ctd), 
                self._path('beta', 'policy', self.ctd), b2_out
            )

            # ---------------------------------------------------------
            # 2. DEFINE DEPENDENCY CHAINS
            # We create async wrappers that explicitly `await` specific futures.
            # ---------------------------------------------------------
            
            async def run_a2_when_ready():
                await task_a1  # Wait ONLY for A1 to finish
                logging.info("A1 complete. Starting A2 immediately.")
                return await loop.run_in_executor(
                    pool, alpha_a2_flow_risk,
                    self._path('alpha', 'flow', self.ctd), a1_out, a2_out
                )

            async def run_c1_when_ready():
                # Wait for both A1 and B1, but NOT B2 or A2
                await asyncio.gather(task_a1, task_b1) 
                logging.info("A1 and B1 complete. Starting C1 immediately.")
                return await loop.run_in_executor(
                    pool, consolidated_c1_report,
                    a1_out, b1_out, c1_out
                )

            # ---------------------------------------------------------
            # 3. EXECUTE THE CHAINS
            # Schedule the dependent chains on the event loop
            # ---------------------------------------------------------
            task_a2 = asyncio.create_task(run_a2_when_ready())
            task_c1 = asyncio.create_task(run_c1_when_ready())

            # ---------------------------------------------------------
            # 4. AWAIT ALL TERMINAL NODES
            # Keep the main program running until the very last tasks finish
            # ---------------------------------------------------------
            await asyncio.gather(task_a1, task_b1, task_b2, task_a2, task_c1)
            
        logging.info("=== Pipeline Execution Complete ===")