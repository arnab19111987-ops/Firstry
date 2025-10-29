from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Dict


IssueType = Literal[
    "lint-fixable",
    "lint-manual",
    "type-error",
    "security",
    "test-fail",
    "coverage-low",
]


@dataclass
class Issue:
    # one row in the “Detailed Issues” table
    kind: IssueType  # e.g. "lint-fixable", "type-error"
    file: str  # filename or pseudo ("(pytest)")
    line: Optional[int]  # line number if known
    message: str  # human-readable message
    autofixable: bool  # True if safe tooling can fix automatically


@dataclass
class SectionSummary:
    # rollup for each section in the report
    name: str  # "Lint / Style", "Types", "Security / Secrets", "Tests & Coverage"
    autofixable_count: int  # how many issues in this section are autofixable
    manual_count: int  # how many issues in this section require human attention
    notes: List[str]  # extra info (e.g. "0 type errors." / "HIGH severity present.")
    ci_blocking: bool  # does CI block on this category?


@dataclass
class ScanResult:
    # full scan output that gets printed in the summary and detail views
    sections: List[SectionSummary] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)

    total_autofixable: int = 0
    total_manual: int = 0

    commit_safe: bool = False

    coverage_pct: float = 0.0
    coverage_required: float = 80.0

    files_scanned: int = 0
    gate_name: str = "pre-commit"

    # list of shell commands the scanner recommends to autofix issues
    # scanner.py may also set this attribute at runtime; declare it here
    # so static type checking (mypy) and consumers can rely on the attribute.
    autofix_cmds: List[str] = field(default_factory=list)
    # Security grouping counts (scanner will populate these when available)
    high_risk_unreviewed: int = 0
    known_risky_but_baselined: int = 0
    # File-level lists for quick triage
    high_risk_unreviewed_files: List[str] = field(default_factory=list)
    known_risky_but_baselined_files: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        """
        Structured form that could be JSON dumped or logged.
        """
        return {
            "gate_name": self.gate_name,
            "files_scanned": self.files_scanned,
            "commit_safe": self.commit_safe,
            "coverage_pct": self.coverage_pct,
            "coverage_required": self.coverage_required,
            "total_autofixable": self.total_autofixable,
            "total_manual": self.total_manual,
            "sections": [
                {
                    "name": s.name,
                    "autofixable_count": s.autofixable_count,
                    "manual_count": s.manual_count,
                    "notes": list(s.notes),
                    "ci_blocking": s.ci_blocking,
                }
                for s in self.sections
            ],
            "issues": [
                {
                    "kind": i.kind,
                    "file": i.file,
                    "line": i.line,
                    "message": i.message,
                    "autofixable": i.autofixable,
                }
                for i in self.issues
            ],
            # include autofix_cmds in the dict if scanner attached it
            "autofix_cmds": getattr(self, "autofix_cmds", []),
            "high_risk_unreviewed": getattr(self, "high_risk_unreviewed", 0),
            "known_risky_but_baselined": getattr(self, "known_risky_but_baselined", 0),
            "high_risk_unreviewed_files": getattr(
                self, "high_risk_unreviewed_files", []
            ),
            "known_risky_but_baselined_files": getattr(
                self, "known_risky_but_baselined_files", []
            ),
        }
