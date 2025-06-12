from datetime import datetime, timedelta, timezone
from models import db, Blocklist, Safelist, Historical
import logging
from app import create_app 

app = create_app()  # Fixed: call create_app() directly

def cleanup_expired_ips(expiration_days=90):
    """
    Move entries that expired more than expiration_days ago to the Historical table
    """
    try:
        # Calculate cutoff date
        now = datetime.now(timezone.utc)
        cutoff_date = now - timedelta(days=expiration_days)
        
        logging.info(f"Current time (UTC): {now}")
        logging.info(f"Cutoff date (UTC): {cutoff_date}")
        
        # Find entries whose expiration dates are older than cutoff
        expired_blocks = Blocklist.query.filter(
            Blocklist.expires_at <= cutoff_date
        ).all()
        
        expired_safelist = Safelist.query.filter(
            Safelist.expires_at <= cutoff_date
        ).all()
        
        total_moved = 0

        # Move from blocklist
        for entry in expired_blocks:
            db.session.add(Historical(
                ip_address=entry.ip_address,
                created_by=entry.created_by,
                comment=entry.comment,
                added_at=entry.added_at,
                duration=entry.duration,
                blocks_count=entry.blocks_count,
                unblocked_at=now
            ))
            db.session.delete(entry)
            total_moved += 1

        # Move from safelist
        for entry in expired_safelist:
            db.session.add(Historical(
                ip_address=entry.ip_address,
                created_by=entry.created_by,
                comment=entry.comment,
                added_at=entry.added_at,
                duration=entry.duration,
                blocks_count=None,
                unblocked_at=now
            ))
            db.session.delete(entry)
            total_moved += 1

        db.session.commit()
        logging.info(f"Moved {total_moved} entries to Historical table")
        return total_moved
        
    except Exception as e:
        logging.error(f"Error during cleanup: {str(e)}")
        db.session.rollback()
        return 0
    finally:
        db.session.close()
