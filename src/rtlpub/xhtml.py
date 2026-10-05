"""Small XHTML checks with inherited language and direction."""

import unicodedata
from dataclasses import dataclass
from xml.etree.ElementTree import Element

from .models import Finding, InputError, Limits, Report
from .safeio import parse_xml
from .text import PERSIAN_LANGS, check_text

XHTML = "http://www.w3.org/1999/xhtml"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


@dataclass(frozen=True)
class Document:
    ids: frozenset[str]
    references: tuple[tuple[str, str], ...]


def check_xhtml(
    data: bytes, path: str, report: Report, limits: Limits, fallback_language: str = ""
) -> Document:
    root = parse_xml(data, limits)
    if root.tag != f"{{{XHTML}}}html":
        raise InputError("XHTML_ROOT", "Expected a namespaced XHTML html element.")
    ids: set[str] = set()
    references: list[tuple[str, str]] = []
    previous_heading = 0
    root_language = root.get(XML_LANG, root.get("lang", ""))
    if not root_language:
        report.add(
            Finding(
                "XHTML_LANGUAGE",
                "warning",
                path,
                "Document root does not declare its language.",
                "/html",
            )
        )
    if root_language.split("-")[0].lower() in PERSIAN_LANGS and not root.get("dir"):
        report.add(
            Finding(
                "XHTML_DIRECTION",
                "warning",
                path,
                "Persian document root has no direction declaration.",
                "/html",
            )
        )

    def visit(element: Element, language: str, direction: str, location: str) -> None:
        nonlocal previous_heading
        tag = element.tag.rsplit("}", 1)[-1]
        own_language = element.get(XML_LANG, element.get("lang", language))
        own_direction = element.get("dir", "auto" if tag == "bdi" else direction).lower()
        if "dir" in element.attrib and own_direction not in {"rtl", "ltr", "auto"}:
            report.add(
                Finding(
                    "XHTML_DIR_VALUE",
                    "error",
                    path,
                    "Direction must be rtl, ltr or auto.",
                    location,
                )
            )
        if XML_LANG in element.attrib and "lang" in element.attrib:
            if element.attrib[XML_LANG].lower() != element.attrib["lang"].lower():
                report.add(
                    Finding(
                        "XHTML_LANG_CONFLICT",
                        "warning",
                        path,
                        "lang and xml:lang disagree.",
                        location,
                    )
                )
        identifier = element.get("id")
        if identifier:
            if identifier in ids:
                report.add(
                    Finding(
                        "XHTML_DUPLICATE_ID",
                        "error",
                        path,
                        "Duplicate element identifier.",
                        location,
                    )
                )
            ids.add(identifier)
        if tag == "img" and "alt" not in element.attrib:
            report.add(
                Finding("XHTML_ALT", "warning", path, "Image has no alt attribute.", location)
            )
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            if level > previous_heading + 1:
                report.add(
                    Finding(
                        "XHTML_HEADING", "warning", path, "Heading level skips a level.", location
                    )
                )
            previous_heading = level
        for attribute in ("href", "src", "poster", "data", "{http://www.w3.org/1999/xlink}href"):
            if element.get(attribute):
                references.append((element.attrib[attribute], location))

        def text_direction(text: str) -> None:
            if (
                own_language.lower().split("-")[0] in PERSIAN_LANGS
                and own_direction == "ltr"
                and sum(unicodedata.bidirectional(char) in {"R", "AL"} for char in text) >= 12
            ):
                report.add(
                    Finding(
                        "XHTML_EFFECTIVE_DIRECTION",
                        "warning",
                        path,
                        "Substantial Persian text inherits LTR; review author intent.",
                        location,
                    )
                )

        if element.text and tag not in {"script", "style"}:
            text_direction(element.text)
            check_text(element.text, path, report, own_language, location, False)
        counts: dict[str, int] = {}
        for child in element:
            child_tag = child.tag.rsplit("}", 1)[-1]
            counts[child_tag] = counts.get(child_tag, 0) + 1
            visit(
                child, own_language, own_direction, f"{location}/{child_tag}[{counts[child_tag]}]"
            )
            if child.tail:
                text_direction(child.tail)
                check_text(child.tail, path, report, own_language, location, False)

    visit(root, root_language or fallback_language, root.get("dir", "ltr"), "/html")
    return Document(frozenset(ids), tuple(references))
