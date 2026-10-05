"""Stable report values and fixed default input budgets."""

from dataclasses import asdict, dataclass, field
from typing import Literal

Severity = Literal["info", "warning", "error"]
RANK: dict[str, int] = {"info": 0, "warning": 1, "error": 2}


@dataclass(frozen=True)
class Limits:
    files: int = 1000
    file_bytes: int = 4 * 1024 * 1024
    total_bytes: int = 64 * 1024 * 1024
    archive_bytes: int = 32 * 1024 * 1024
    zip_ratio: int = 100
    xml_depth: int = 128
    xml_nodes: int = 100_000
    findings: int = 10_000


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    path: str
    message: str
    location: str | None = None
    line: int | None = None
    column: int | None = None


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list[Finding])
    checked_files: int = 0
    invalid_input: bool = False
    _cap: int = 10_000

    def add(self, finding: Finding) -> None:
        if len(self.findings) < self._cap:
            self.findings.append(finding)
        elif not self.invalid_input:
            self.invalid_input = True
            self.findings.append(
                Finding(
                    "INPUT_FINDING_LIMIT",
                    "error",
                    ".",
                    "Finding budget exceeded; report is incomplete.",
                )
            )

    def exit_code(self, threshold: str = "error") -> int:
        if self.invalid_input:
            return 2
        return int(any(RANK[f.severity] >= RANK[threshold] for f in self.findings))

    def to_dict(self, threshold: str = "error") -> dict[str, object]:
        ordered = sorted(
            self.findings,
            key=lambda f: (f.path, f.location or "", f.line or 0, f.column or 0, f.rule, f.message),
        )
        return {
            "schema_version": "1.0",
            "tool_version": "0.1.0",
            "threshold": threshold,
            "exit_code": self.exit_code(threshold),
            "checked_files": self.checked_files,
            "status": "invalid_input" if self.invalid_input else "checked",
            "findings": [asdict(f) for f in ordered],
        }


class InputError(Exception):
    """A controlled failure; never include raw exceptions or input excerpts."""

    def __init__(self, rule: str, message: str):
        super().__init__(message)
        self.rule = rule
