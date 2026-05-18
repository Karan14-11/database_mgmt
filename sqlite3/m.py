import argparse
import asyncio
import sys
from p import ETLPipeline

def main():
    parser = argparse.ArgumentParser(description="Deterministic Exchange ETL Engine")
    parser.add_argument(
        '--ctd', 
        type=str, 
        required=True, 
        help="Current Trading Day (YYYYMMDD)"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize and run the async orchestrator
        pipeline = ETLPipeline(ctd=args.ctd)
        asyncio.run(pipeline.run())
    except Exception as e:
        print(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()