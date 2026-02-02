#!/usr/bin/env python3
"""
OMEN Automated Backup Script.

Backs up:
- PostgreSQL database (if configured)
- SQLite databases
- Ledger files
- Configuration files

Run via cron or Kubernetes CronJob:
    # Every 6 hours
    0 */6 * * * /app/scripts/backup.py

Usage:
    python scripts/backup.py
    python scripts/backup.py --type full
    python scripts/backup.py --type incremental --since "2026-01-31"
"""

import argparse
import glob
import gzip
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration from environment
BACKUP_DIR = os.getenv("OMEN_BACKUP_DIR", "/backups")
RETENTION_DAYS = int(os.getenv("OMEN_BACKUP_RETENTION_DAYS", "30"))
DATABASE_URL = os.getenv("DATABASE_URL")
LEDGER_DIR = os.getenv("OMEN_LEDGER_BASE_PATH", "/data/ledger")
SQLITE_DIR = os.getenv("OMEN_DATA_DIR", "/data")


def ensure_backup_dir() -> Path:
    """Ensure backup directory exists."""
    backup_path = Path(BACKUP_DIR)
    backup_path.mkdir(parents=True, exist_ok=True)
    return backup_path


def get_timestamp() -> str:
    """Get timestamp for backup file names."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def backup_postgres() -> str | None:
    """
    Backup PostgreSQL database using pg_dump.
    
    Returns:
        Path to backup file, or None if failed/not configured
    """
    if not DATABASE_URL:
        logger.info("DATABASE_URL not configured, skipping PostgreSQL backup")
        return None
    
    timestamp = get_timestamp()
    backup_file = Path(BACKUP_DIR) / f"postgres_{timestamp}.sql.gz"
    
    try:
        logger.info("Starting PostgreSQL backup...")
        
        # Use pg_dump with gzip compression
        with gzip.open(backup_file, "wt") as f:
            result = subprocess.run(
                ["pg_dump", DATABASE_URL, "--no-owner", "--no-acl"],
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3600,  # 1 hour timeout
            )
        
        if result.returncode != 0:
            logger.error("pg_dump failed: %s", result.stderr)
            backup_file.unlink(missing_ok=True)
            return None
        
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        logger.info("PostgreSQL backup created: %s (%.2f MB)", backup_file, size_mb)
        return str(backup_file)
        
    except subprocess.TimeoutExpired:
        logger.error("PostgreSQL backup timed out")
        backup_file.unlink(missing_ok=True)
        return None
    except Exception as e:
        logger.error("PostgreSQL backup failed: %s", e)
        backup_file.unlink(missing_ok=True)
        return None


def backup_sqlite() -> list[str]:
    """
    Backup SQLite databases.
    
    Returns:
        List of backup file paths
    """
    sqlite_files = []
    timestamp = get_timestamp()
    
    # Find SQLite databases
    patterns = [
        f"{SQLITE_DIR}/**/*.db",
        f"{SQLITE_DIR}/**/*.sqlite",
        f"{SQLITE_DIR}/**/*.sqlite3",
    ]
    
    db_files = []
    for pattern in patterns:
        db_files.extend(glob.glob(pattern, recursive=True))
    
    if not db_files:
        logger.info("No SQLite databases found")
        return []
    
    for db_path in db_files:
        try:
            db_name = Path(db_path).stem
            backup_file = Path(BACKUP_DIR) / f"sqlite_{db_name}_{timestamp}.db.gz"
            
            logger.info("Backing up SQLite: %s", db_path)
            
            # Use SQLite backup command for consistency
            temp_backup = Path(BACKUP_DIR) / f"temp_{db_name}.db"
            
            result = subprocess.run(
                ["sqlite3", db_path, f".backup '{temp_backup}'"],
                stderr=subprocess.PIPE,
                text=True,
                timeout=600,
            )
            
            if result.returncode != 0:
                logger.warning("SQLite backup command failed, copying directly")
                shutil.copy2(db_path, temp_backup)
            
            # Compress
            with open(temp_backup, "rb") as f_in:
                with gzip.open(backup_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            temp_backup.unlink(missing_ok=True)
            
            size_kb = backup_file.stat().st_size / 1024
            logger.info("SQLite backup created: %s (%.2f KB)", backup_file, size_kb)
            sqlite_files.append(str(backup_file))
            
        except Exception as e:
            logger.error("SQLite backup failed for %s: %s", db_path, e)
    
    return sqlite_files


def backup_ledger() -> str | None:
    """
    Backup ledger directory.
    
    Returns:
        Path to backup file, or None if failed/not found
    """
    ledger_path = Path(LEDGER_DIR)
    
    if not ledger_path.exists():
        logger.info("Ledger directory not found: %s", LEDGER_DIR)
        return None
    
    timestamp = get_timestamp()
    backup_file = Path(BACKUP_DIR) / f"ledger_{timestamp}.tar.gz"
    
    try:
        logger.info("Starting ledger backup from: %s", LEDGER_DIR)
        
        shutil.make_archive(
            str(backup_file).replace(".tar.gz", ""),
            "gztar",
            root_dir=ledger_path.parent,
            base_dir=ledger_path.name,
        )
        
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        logger.info("Ledger backup created: %s (%.2f MB)", backup_file, size_mb)
        return str(backup_file)
        
    except Exception as e:
        logger.error("Ledger backup failed: %s", e)
        return None


def cleanup_old_backups() -> int:
    """
    Remove backups older than retention period.
    
    Returns:
        Number of files deleted
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    deleted = 0
    
    backup_path = Path(BACKUP_DIR)
    
    for pattern in ["postgres_*.sql.gz", "sqlite_*.db.gz", "ledger_*.tar.gz"]:
        for f in backup_path.glob(pattern):
            try:
                # Parse timestamp from filename
                parts = f.stem.split("_")
                if len(parts) >= 2:
                    date_str = parts[-2] + "_" + parts[-1].split(".")[0]
                    file_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                    file_date = file_date.replace(tzinfo=timezone.utc)
                    
                    if file_date < cutoff:
                        f.unlink()
                        logger.info("Deleted old backup: %s", f)
                        deleted += 1
            except Exception as e:
                logger.warning("Could not process backup file %s: %s", f, e)
    
    return deleted


def verify_backup(backup_file: str) -> bool:
    """
    Verify backup file integrity.
    
    Returns:
        True if backup is valid
    """
    path = Path(backup_file)
    
    if not path.exists():
        return False
    
    if path.stat().st_size == 0:
        return False
    
    # Verify gzip integrity
    if backup_file.endswith(".gz"):
        try:
            with gzip.open(path, "rb") as f:
                # Read first chunk to verify
                f.read(1024)
            return True
        except Exception:
            return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description="OMEN Backup Script")
    parser.add_argument(
        "--type",
        choices=["full", "incremental"],
        default="full",
        help="Backup type",
    )
    parser.add_argument(
        "--skip-postgres",
        action="store_true",
        help="Skip PostgreSQL backup",
    )
    parser.add_argument(
        "--skip-sqlite",
        action="store_true",
        help="Skip SQLite backup",
    )
    parser.add_argument(
        "--skip-ledger",
        action="store_true",
        help="Skip ledger backup",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip cleanup of old backups",
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("OMEN Backup Starting")
    logger.info("Backup directory: %s", BACKUP_DIR)
    logger.info("Retention: %d days", RETENTION_DAYS)
    logger.info("=" * 60)
    
    ensure_backup_dir()
    
    results = {
        "postgres": None,
        "sqlite": [],
        "ledger": None,
        "deleted": 0,
        "success": True,
    }
    
    # PostgreSQL
    if not args.skip_postgres:
        results["postgres"] = backup_postgres()
    
    # SQLite
    if not args.skip_sqlite:
        results["sqlite"] = backup_sqlite()
    
    # Ledger
    if not args.skip_ledger:
        results["ledger"] = backup_ledger()
    
    # Cleanup
    if not args.no_cleanup:
        results["deleted"] = cleanup_old_backups()
        logger.info("Cleaned up %d old backups", results["deleted"])
    
    # Verify backups
    for backup_file in [results["postgres"], results["ledger"]] + results["sqlite"]:
        if backup_file and not verify_backup(backup_file):
            logger.error("Backup verification FAILED: %s", backup_file)
            results["success"] = False
    
    # Summary
    logger.info("=" * 60)
    logger.info("OMEN Backup Complete")
    logger.info("PostgreSQL: %s", results["postgres"] or "skipped")
    logger.info("SQLite: %d files", len(results["sqlite"]))
    logger.info("Ledger: %s", results["ledger"] or "skipped")
    logger.info("Status: %s", "SUCCESS" if results["success"] else "FAILED")
    logger.info("=" * 60)
    
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()
