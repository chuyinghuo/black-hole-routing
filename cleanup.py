import sys
import os
import time
import logging
from datetime import datetime, timedelta, timezone
from app import create_app
 
# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from init_db import db
from app import create_app
from utils import cleanup_expired_ips
 
# Configure logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
 
CLEANUP_INTERVAL = 86400  # 24 hours
 
def run_continuous_cleanup():
    """Run cleanup every CLEANUP_INTERVAL seconds"""
    app = create_app()
    
    with app.app_context():
        while True:
            try:
                start_time = time.time()
                logging.info(f"Running cleanup cycle at {datetime.now(timezone.utc)}")
                
                cleanup_expired_ips()
                
                # Calculate sleep time to maintain exact interval
                elapsed = time.time() - start_time
                sleep_time = max(0, CLEANUP_INTERVAL - elapsed)
                logging.info(f"Next cleanup in {sleep_time:.0f} seconds")
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logging.info("Cleanup service stopped by user")
                break
            except Exception as e:
                logging.error(f"Unexpected error: {str(e)}")
                time.sleep(CLEANUP_INTERVAL)  # Wait full interval on error
 
if __name__ == "__main__":
    logging.info(f"Starting cleanup service (interval: {CLEANUP_INTERVAL} seconds)...")
    run_continuous_cleanup()