"""One safe dispatcher for files and bounded directory trees."""

import os
from dataclasses import replace
from pathlib import Path

from .epub import check_epub
from .models import Finding, InputError, Limits, Report
from .safeio import linked, read_file
from .text import check_text
from .xhtml import check_xhtml

SUPPORTED = {".txt", ".xhtml", ".html", ".epub"}


def check_path(path: str | Path, limits: Limits | None = None, language: str = "fa") -> Report:
    limits = limits or Limits()
    report = Report(_cap=limits.findings)
    original = Path(path).absolute()
    total = 0

    def failed(error: InputError, relative: str) -> None:
        report.invalid_input = True
        report.add(Finding(error.rule, "error", relative, str(error)))

    def check_one(file: Path, relative: str) -> None:
        nonlocal total
        maximum = limits.archive_bytes if file.suffix.lower() == ".epub" else limits.file_bytes
        try:
            data = read_file(file, min(maximum, limits.total_bytes - total))
            total += len(data)
            report.checked_files += 1
            if file.suffix.lower() == ".epub":
                total += check_epub(
                    data, relative, report, replace(limits, total_bytes=limits.total_bytes - total)
                )
            elif file.suffix.lower() in {".xhtml", ".html"}:
                check_xhtml(data, relative, report, limits)
            else:
                check_text(data.decode("utf-8-sig"), relative, report, language)
        except InputError as exc:
            failed(exc, relative)
        except UnicodeError:
            failed(InputError("INPUT_ENCODING", "Plain text must be UTF-8."), relative)
        except (OSError, ValueError):
            failed(InputError("INPUT_READ", "Input could not be safely read."), relative)

    try:
        if any(linked(part) for part in (original, *original.parents)):
            raise InputError("INPUT_SYMLINK", "Symlink paths and ancestors are unsupported.")
        if original.is_file():
            if original.suffix.lower() not in SUPPORTED:
                raise InputError("INPUT_UNSUPPORTED", "Input extension is unsupported.")
            check_one(original, original.name)
        elif original.is_dir():
            visited = 0

            def walk_error(error: OSError) -> None:
                raise error

            for directory, folders, files in os.walk(
                original, followlinks=False, onerror=walk_error
            ):
                folders.sort()
                files.sort()
                for name in folders + files:
                    visited += 1
                    candidate = Path(directory) / name
                    relative = candidate.relative_to(original).as_posix()
                    if visited > limits.files:
                        raise InputError("INPUT_COUNT", "Directory exceeds the entry count budget.")
                    if linked(candidate):
                        failed(
                            InputError("INPUT_SYMLINK", "Symlink entries are unsupported."),
                            relative,
                        )
                        if name in folders:
                            folders.remove(name)
                        continue
                    if name in files and candidate.suffix.lower() in SUPPORTED:
                        check_one(candidate, relative)
            if not report.checked_files and not report.invalid_input:
                raise InputError(
                    "INPUT_EMPTY", "Directory contains no supported publication files."
                )
        else:
            raise InputError(
                "INPUT_PATH", "Input path is missing or is not a regular file/directory."
            )
    except InputError as exc:
        failed(exc, ".")
    except OSError:
        failed(InputError("INPUT_READ", "Input directory could not be safely read."), ".")
    return report
