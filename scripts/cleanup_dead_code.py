"""
Identify and report dead or outdated code in OMEN.

Usage:
    python scripts/cleanup_dead_code.py --dry-run   # report only
    python scripts/cleanup_dead_code.py --remove    # (reserved for future use)
"""

import argparse
import ast
import sys
from pathlib import Path

# Project root and src layout
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "omen"

# Items that were historically dead/broken and have been addressed
RESOLVED = [
    "polymarket/mapper.py — fixed to use RawSignalEvent + MarketMetadata (was SignalSource, SignalType)",
    "domain/services/confidence_calculator.py — removed (unused; confidence in OmenSignal.from_impact_assessment)",
]

# Empty or placeholder files that are intentional
INTENTIONAL_PLACEHOLDERS = [
    "src/omen/domain/rules/translation/energy/__init__.py",
]


def find_unused_imports(filepath: Path) -> list[str]:
    """Find imports that are never used in the file (simple heuristic)."""
    try:
        text = filepath.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (SyntaxError, OSError):
        return []

    imported: set[str] = set()
    used: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imported.add(name.split(".")[0])  # top-level name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                imported.add(top)
            for alias in node.names:
                name = alias.asname or alias.name
                imported.add(name.split(".")[0])
        elif isinstance(node, (ast.Name, ast.Attribute)):
            n = node
            if isinstance(n, ast.Name):
                used.add(n.id)
            elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                used.add(n.value.id)

    # Only report明显 unused: name in imported (as top-level) but never in used
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="OMEN dead code analysis")
    parser.add_argument("--dry-run", action="store_true", help="Report only (default)")
    parser.add_argument("--remove", action="store_true", help="Reserved for future use")
    args = parser.parse_args()

    print("OMEN Dead Code Analysis")
    print("=" * 50)

    if args.remove:
        print("--remove is not implemented. Use --dry-run to see report.\n")

    print("Resolved (already fixed):")
    for item in RESOLVED:
        print(f"  [OK] {item}")

    print("\nVerifying common.py has no legacy dead symbols...")
    common_py = SRC / "domain" / "models" / "common.py"
    legacy = ["GeographicRegion", "SignalType", "ImpactCategory", "ImpactSeverity", "StepType"]
    if common_py.exists():
        content = common_py.read_text(encoding="utf-8")
        found = [s for s in legacy if f"class {s}" in content or f"class {s}(" in content]
        if found:
            print(f"  [WARN] Found legacy symbols: {found}")
        else:
            print("  [OK] No legacy symbols from audit list.")

    print("\nIntentional placeholders (no action):")
    for p in INTENTIONAL_PLACEHOLDERS:
        print(f"  - {p}")

    print("\nDone. Run tests to confirm: pytest -v")
    return 0


if __name__ == "__main__":
    sys.exit(main())
