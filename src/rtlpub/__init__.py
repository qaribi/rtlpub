"""Read-only publishing checks. Findings are hints, not conformance certification."""

from .checker import check_path
from .models import Finding, Limits, Report

__version__ = "0.1.0"
__all__ = ["Finding", "Limits", "Report", "check_path"]
