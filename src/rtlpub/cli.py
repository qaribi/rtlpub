"""Human and stable JSON command-line output without raw error details."""

import argparse
import json
import sys
from collections.abc import Sequence

from .checker import check_path
from .models import Finding, Report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rtlpub", description="Offline publishing preflight")
    parser.add_argument("--version", action="version", version="rtlpub 0.1.0")
    subcommands = parser.add_subparsers(dest="command", required=True)
    check = subcommands.add_parser("check", help="Read text, XHTML or EPUB without changing input")
    check.add_argument("path")
    check.add_argument("--format", choices=("human", "json"), default="human")
    check.add_argument("--fail-on", choices=("error", "warning", "info"), default="error")
    check.add_argument(
        "--text-language",
        choices=("fa", "ar", "und"),
        default="fa",
        help="Language for plain text only; XHTML uses inherited declarations",
    )
    arguments = parser.parse_args(argv)
    try:
        report = check_path(arguments.path, language=arguments.text_language)
    except Exception:
        report = Report(invalid_input=True)
        report.add(Finding("INPUT_RUNTIME", "error", ".", "Unexpected processing failure."))
    output = report.to_dict(arguments.fail_on)
    try:
        if arguments.format == "json":
            print(json.dumps(output, ensure_ascii=True, sort_keys=True))
        else:
            for finding in report.findings:
                where = finding.path
                if finding.line is not None:
                    where += f":{finding.line}:{finding.column}"
                elif finding.location:
                    where += f":{finding.location}"
                print(
                    f"{finding.severity.upper()} {finding.rule} "
                    f"{json.dumps(where, ensure_ascii=True)}: {finding.message}"
                )
            print(
                f"Checked {report.checked_files} file(s); {len(report.findings)} finding(s); "
                f"exit {report.exit_code(arguments.fail_on)}."
            )
    except (OSError, UnicodeError):
        return 2
    return report.exit_code(arguments.fail_on)


if __name__ == "__main__":
    sys.exit(main())
