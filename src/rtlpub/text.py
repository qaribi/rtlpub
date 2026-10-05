"""Conservative diagnostics: no normalization, rewriting or excerpts."""

import unicodedata

from .models import Finding, Report

PERSIAN_LANGS = {"fa", "pes"}
BIDI_CONTROLS = {
    chr(n) for n in (0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069)
}


def check_text(
    text: str,
    path: str,
    report: Report,
    language: str = "fa",
    location: str | None = None,
    positions: bool = True,
) -> None:
    persian = language.lower().split("-")[0] in PERSIAN_LANGS
    line = column = 1
    for index, char in enumerate(text):
        rule = message = ""
        if char in BIDI_CONTROLS:
            rule, message = "TEXT_BIDI_CONTROL", "Explicit bidi control needs manual review."
        elif persian and char in {"ي", "ك"}:
            rule, message = "TEXT_ARABIC_LETTER", "Arabic yeh/kaf in Persian-language text."
        elif char == "\u200c":
            left = text[index - 1] if index else ""
            right = text[index + 1] if index + 1 < len(text) else ""
            if not left or not right or left.isspace() or right.isspace() or left == char:
                rule, message = (
                    "TEXT_ZWNJ_BOUNDARY",
                    "Half-space at a boundary needs manual review.",
                )
        elif char == "\ufeff" and index != 0:
            rule, message = "TEXT_EMBEDDED_BOM", "Byte-order mark inside text needs manual review."
        if rule:
            report.add(
                Finding(
                    rule,
                    "warning",
                    path,
                    message,
                    location,
                    line if positions else None,
                    column if positions else None,
                )
            )
        if char == "\n":
            line, column = line + 1, 1
        else:
            column += 1
    if unicodedata.normalize("NFC", text) != text:
        report.add(
            Finding(
                "TEXT_NON_NFC",
                "warning",
                path,
                "Text is not NFC; inspect before any normalization.",
                location,
            )
        )
