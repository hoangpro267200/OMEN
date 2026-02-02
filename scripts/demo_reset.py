"""
One-click demo reset for competition.
Resets all state to initial demo conditions.

Usage:
    python -m scripts.demo_reset

Expects: OMEN_LEDGER_BASE_PATH, RISKCAST_DB_PATH (or /data/ledger, /data/riskcast).
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add repo root for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

logger = logging.getLogger(__name__)


async def reset_demo() -> None:
    """Reset demo to initial state."""
    print("🔄 Resetting demo environment...")

    # 1. Clear ledger
    ledger_path = Path(os.environ.get("OMEN_LEDGER_BASE_PATH", "/data/ledger"))
    if ledger_path.exists():
        import shutil
        shutil.rmtree(ledger_path)
    ledger_path.mkdir(parents=True, exist_ok=True)
    print("  ✓ Ledger cleared")

    # 2. Clear RiskCast DB (signals.db and reconcile_state.db)
    riskcast_db = os.environ.get("RISKCAST_DB_PATH", "/data/riskcast/signals.db")
    db_path = Path(riskcast_db)
    if db_path.exists():
        db_path.unlink()
        print("  ✓ RiskCast DB cleared")
    state_path = db_path.parent / "reconcile_state.db"
    if state_path.exists():
        state_path.unlink()
        print("  ✓ Reconcile state cleared")

    # 3. Seed fresh demo data
    from scripts.seed_demo_data import create_demo_signals
    await create_demo_signals(total_signals=10, processed_count=8)
    print("  ✓ Demo data seeded")

    print("\n✅ Demo reset complete!")
    print("\nInitial state:")
    print("  • Ledger: 10 signals")
    print("  • RiskCast: 8 processed (2 missing)")
    print("  • Ready for reconcile demo")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(reset_demo())
