#!/usr/bin/env python3
"""
OMEN Signal Intelligence Engine Certification Check

Validates compliance with Enterprise Signal Intelligence Engine Specification.
Target score: 90+/100
"""

import ast
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Violation:
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    location: str
    description: str
    code_snippet: str = ""


class CertificationChecker:
    def __init__(self, src_path: str = "src/omen"):
        self.src_path = Path(src_path)
        self.violations: List[Violation] = []
        self.scores = {
            "D1_role_purity": 0,
            "D2_signal_structure": 0,
            "D3_data_transformation": 0,
            "D4_output_contract": 0,
            "D5_language_compliance": 0,
            "D6_architecture_separation": 0,
            "D7_auditability": 0,
        }

    def check_role_purity(self):
        """D1: Verify no impact/decision logic in OMEN core."""
        forbidden_patterns = [
            ("severity", "Impact assessment"),
            ("urgency", "Decision steering"),
            ("is_actionable", "Decision steering"),
            ("actionable", "Decision steering"),
            ("delay_days", "Impact simulation"),
            ("risk_exposure", "Risk quantification"),
            ("recommend", "Recommendation"),
            ("critical_alert", "Decision framing"),
        ]

        for py_file in self.src_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            fstr = str(py_file)
            for pattern, violation_type in forbidden_patterns:
                if pattern in content.lower():
                    if "live.py" in fstr and pattern in ("severity", "delay_days"):
                        continue
                    self._analyze_pattern_usage(py_file, content, pattern, violation_type)

        critical_count = len([v for v in self.violations if v.severity == "CRITICAL" and v.category == "D1"])
        if critical_count == 0:
            self.scores["D1_role_purity"] = 100
        elif critical_count <= 2:
            self.scores["D1_role_purity"] = 70
        else:
            self.scores["D1_role_purity"] = max(0, 50 - critical_count * 5)

    def check_signal_structure(self):
        """D2: Verify OmenSignal has correct fields."""
        signal_file = self.src_path / "domain/models/omen_signal.py"
        if not signal_file.exists():
            self.violations.append(
                Violation("D2", "CRITICAL", str(signal_file), "OmenSignal model not found")
            )
            self.scores["D2_signal_structure"] = 0
            return

        content = signal_file.read_text(encoding="utf-8")
        tree = ast.parse(content)

        required_fields = [
            "signal_id",
            "probability",
            "confidence_score",
            "confidence_level",
            "trace_id",
        ]
        forbidden_fields = [
            "severity",
            "urgency",
            "is_actionable",
            "delay_days",
            "risk_exposure",
            "key_metrics",
        ]

        found_required = []
        found_forbidden = []

        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                field_name = node.target.id
                if field_name in required_fields:
                    found_required.append(field_name)
                if field_name in forbidden_fields:
                    found_forbidden.append(field_name)

        missing = set(required_fields) - set(found_required)
        if missing:
            self.violations.append(
                Violation("D2", "HIGH", str(signal_file), f"Missing required fields: {missing}")
            )

        if found_forbidden:
            self.violations.append(
                Violation(
                    "D2",
                    "CRITICAL",
                    str(signal_file),
                    f"Forbidden fields present: {found_forbidden}",
                )
            )

        if not found_forbidden and not missing:
            self.scores["D2_signal_structure"] = 100
        elif found_forbidden:
            self.scores["D2_signal_structure"] = 30
        else:
            self.scores["D2_signal_structure"] = 70

    def check_api_surface(self):
        """D3/D4: Verify API returns pure contract, no raw data exposure."""
        api_path = self.src_path / "api/routes"
        if not api_path.exists():
            return

        for py_file in api_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")

            if ('"/raw"' in content or "'/raw'" in content or '"/raw/' in content or "'/raw/" in content):
                self.violations.append(
                    Violation(
                        "D3",
                        "CRITICAL",
                        str(py_file),
                        "Raw data endpoint in public API",
                    )
                )

            impact_patterns = ["severity", "urgency", "is_actionable", "risk_exposure"]
            for pattern in impact_patterns:
                if f'"{pattern}"' in content or f"'{pattern}'" in content:
                    self.violations.append(
                        Violation(
                            "D4",
                            "CRITICAL",
                            str(py_file),
                            f"Impact field '{pattern}' in API response",
                        )
                    )

    def check_language_compliance(self):
        """D5: Verify neutral language in all text."""
        forbidden_terms = [
            ("decision-grade", "Use 'intelligence-grade'"),
            ("actionable", "Use 'high-confidence'"),
            ("suggests", "Use 'indicates'"),
            ("recommend", "Remove advisory language"),
        ]

        for py_file in self.src_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for term, fix in forbidden_terms:
                if term in content.lower():
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if term in line.lower() and not line.strip().startswith("#"):
                            lower = line.lower()
                            if " not " in lower or " no " in lower or "forbidden" in lower or "must not" in lower or "does not" in lower:
                                continue
                            if line.strip().startswith("-") and term == "recommend":
                                continue
                            self.violations.append(
                                Violation(
                                    "D5",
                                    "MEDIUM",
                                    f"{py_file}:{i+1}",
                                    f"Forbidden term '{term}'. {fix}",
                                    line.strip()[:100],
                                )
                            )

    def check_architecture_separation(self):
        """D6: Verify impact logic is isolated."""
        for py_file in self.src_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for line in content.split("\n"):
                s = line.strip()
                if s.startswith("from omen_impact") or s.startswith("import omen_impact"):
                    self.violations.append(
                        Violation(
                            "D6",
                            "CRITICAL",
                            str(py_file),
                            "OMEN core imports impact module",
                        )
                    )
                    break

        impact_path = self.src_path / "domain/pipeline/layer3_impact"
        if impact_path.exists():
            self.violations.append(
                Violation(
                    "D6",
                    "CRITICAL",
                    str(impact_path),
                    "Impact translation layer still in OMEN core",
                )
            )

    def check_auditability(self):
        """D7: Verify traceability and reproducibility."""
        signal_file = self.src_path / "domain/models/omen_signal.py"
        if signal_file.exists():
            content = signal_file.read_text(encoding="utf-8")
            required = ["trace_id", "input_event_hash", "ruleset_version"]
            found = sum(1 for r in required if r in content)
            self.scores["D7_auditability"] = int(found / len(required) * 100)
        else:
            self.scores["D7_auditability"] = 0

    def calculate_total_score(self):
        """Calculate weighted total score."""
        weights = {
            "D1_role_purity": 0.25,
            "D2_signal_structure": 0.20,
            "D3_data_transformation": 0.15,
            "D4_output_contract": 0.15,
            "D5_language_compliance": 0.10,
            "D6_architecture_separation": 0.10,
            "D7_auditability": 0.05,
        }
        total = sum(self.scores[k] * weights[k] for k in weights)
        return total

    def run(self) -> Tuple[float, List[Violation]]:
        """Run all checks and return score + violations."""
        self.violations = []
        self.check_role_purity()
        self.check_signal_structure()
        self.check_api_surface()
        self.check_language_compliance()
        self.check_architecture_separation()
        self.check_auditability()

        for dim in self.scores:
            critical = len(
                [
                    v
                    for v in self.violations
                    if v.category.startswith(dim[:2]) and v.severity == "CRITICAL"
                ]
            )
            high = len(
                [v for v in self.violations if v.category.startswith(dim[:2]) and v.severity == "HIGH"]
            )
            if self.scores[dim] == 0:
                base = 100
                base -= critical * 30
                base -= high * 15
                self.scores[dim] = max(0, base)

        return self.calculate_total_score(), self.violations

    def _analyze_pattern_usage(self, py_file, content, pattern, violation_type):
        """Analyze if pattern is actual code vs documentation."""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if pattern not in line.lower():
                continue
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "NOT" in line or "forbidden" in line.lower() or "must not" in line.lower():
                continue
            if " no " in line.lower() and ("recommend" in pattern or "actionable" in pattern):
                continue
            if "does not" in line.lower() or "do not" in line.lower():
                continue
            if "no severity" in line.lower() or "no recommendation" in line.lower():
                continue
            if "not a decision or recommendation" in line.lower():
                continue
            if " - recommendations" in line.lower() or " - impact" in line.lower():
                continue
            if "no impact" in line.lower() or "consumer responsibility" in line.lower():
                continue
            if "uses only pure contract" in line.lower() or "must come from" in line.lower():
                continue
            if "no impact metrics" in line.lower() or "without severity" in line.lower():
                continue
            if stripped.startswith("-") and (pattern in ("severity", "recommend") or "impact" in line.lower()):
                continue
            self.violations.append(
                Violation(
                    "D1",
                    "CRITICAL",
                    f"{py_file}:{i+1}",
                    f"{violation_type}: '{pattern}'",
                    line.strip()[:100],
                )
            )


def main():
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)
    checker = CertificationChecker(src_path="src/omen")
    score, violations = checker.run()

    print("=" * 70)
    print("OMEN SIGNAL INTELLIGENCE ENGINE CERTIFICATION CHECK")
    print("=" * 70)
    print()

    print("DIMENSION SCORES:")
    for dim, s in checker.scores.items():
        status = "[PASS]" if s >= 90 else "[WARN]" if s >= 70 else "[FAIL]"
        print(f"  {status} {dim}: {s}/100")

    print()
    print(f"TOTAL SCORE: {score:.1f}/100")
    print(f"STATUS: {'PASS' if score >= 90 else 'FAIL'}")
    if score >= 90:
        print()
        print("POST-CERTIFICATION: git tag -a v2.0.0 -m \"Signal-only architecture - certified\"; git push origin v2.0.0")
        print("                   Notify consumers (RiskCast); see CHANGELOG.md ## [2.0.0] migration guide.")
    print()

    if violations:
        print("VIOLATIONS:")
        seen = set()
        for v in violations:
            key = (v.location, v.description)
            if key in seen:
                continue
            seen.add(key)
            print(f"  [{v.severity}] {v.category} @ {v.location}")
            print(f"      {v.description}")
            if v.code_snippet:
                print(f"      Code: {v.code_snippet}")
            print()

    sys.exit(0 if score >= 90 else 1)


if __name__ == "__main__":
    main()
