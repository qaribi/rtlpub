"""Limited EPUB 3 package, reading order and internal-reference checks."""

import posixpath
import re
from urllib.parse import unquote, urlsplit
from xml.etree.ElementTree import Element

from .models import Finding, InputError, Limits, Report
from .safeio import parse_xml, read_zip
from .xhtml import Document, check_xhtml

OPF = "{http://www.idpf.org/2007/opf}"
DC = "{http://purl.org/dc/elements/1.1/}"
CONTAINER = "{urn:oasis:names:tc:opendocument:xmlns:container}"


def resolve_reference(source: str, reference: str) -> tuple[str, str] | None:
    """Resolve local URI paths; valid parent links inside the publication are allowed."""
    try:
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc:
            return None
        if re.search(r"%(?![0-9a-fA-F]{2})", parsed.path + parsed.fragment):
            raise ValueError("percent")
        path = unquote(parsed.path, errors="strict")
        fragment = unquote(parsed.fragment, errors="strict")
    except (ValueError, UnicodeError) as exc:
        raise InputError("EPUB_REFERENCE", "Internal reference has an invalid URI.") from exc
    if "\\" in path or "\0" in path or path.startswith("/") or ":" in path:
        raise InputError("EPUB_REFERENCE", "Internal reference has an unsafe path.")
    destination = (
        posixpath.normpath(posixpath.join(posixpath.dirname(source), path)) if path else source
    )
    if destination in {"..", "."} or destination.startswith("../"):
        raise InputError("EPUB_REFERENCE", "Internal reference escapes the publication root.")
    return destination, fragment


def check_epub(data: bytes, path: str, report: Report, limits: Limits) -> int:
    contents = read_zip(data, limits)
    if contents.get("mimetype") != b"application/epub+zip":
        raise InputError("EPUB_MIMETYPE", "EPUB mimetype is absent or invalid.")
    if "META-INF/encryption.xml" in contents:
        raise InputError(
            "EPUB_ENCRYPTED", "Encrypted or obfuscated EPUB resources are unsupported."
        )
    if "META-INF/container.xml" not in contents:
        raise InputError("EPUB_CONTAINER", "EPUB container document is missing.")
    container = parse_xml(contents["META-INF/container.xml"], limits)
    if container.tag != CONTAINER + "container":
        raise InputError("EPUB_CONTAINER", "EPUB container namespace is invalid.")
    rootfiles = container.findall(CONTAINER + "rootfiles/" + CONTAINER + "rootfile")
    if len(rootfiles) != 1:
        raise InputError("EPUB_CONTAINER", "Exactly one package rootfile is supported.")
    package_uri = rootfiles[0].get("full-path", "")
    if not package_uri:
        raise InputError("EPUB_PACKAGE", "Package rootfile has no path.")
    package_resolved = resolve_reference("container.xml", package_uri)
    if package_resolved is None or package_resolved[1]:
        raise InputError("EPUB_PACKAGE", "Package rootfile must be an internal path.")
    package_path = package_resolved[0]
    if package_path not in contents:
        raise InputError("EPUB_PACKAGE", "Package document is missing.")
    package = parse_xml(contents[package_path], limits)
    if package.tag != OPF + "package" or not package.get("version", "").startswith("3."):
        raise InputError("EPUB_VERSION", "Only EPUB 3 package documents are supported.")
    display_package = path + "!/" + package_path

    def finding(rule: str, message: str, location: str, warning: bool = False) -> None:
        report.add(
            Finding(rule, "warning" if warning else "error", display_package, message, location)
        )

    metadata = package.find(OPF + "metadata")
    language = ""
    for key in ("title", "identifier", "language"):
        values = metadata.findall(DC + key) if metadata is not None else []
        if not any((element.text or "").strip() for element in values):
            finding(
                "EPUB_METADATA", f"Required {key} metadata is absent or empty.", "/package/metadata"
            )
        if key == "language" and values:
            language = (values[0].text or "").strip()
    unique_id = package.get("unique-identifier")
    if (
        not unique_id
        or metadata is None
        or not any(
            item.get("id") == unique_id and (item.text or "").strip()
            for item in metadata.findall(DC + "identifier")
        )
    ):
        finding(
            "EPUB_IDENTIFIER",
            "unique-identifier does not resolve to identifier metadata.",
            "/package",
        )
    manifest = package.find(OPF + "manifest")
    items: dict[str, tuple[str, str]] = {}
    destinations: set[str] = set()
    nav_count = 0
    if manifest is None or not list(manifest):
        finding("EPUB_MANIFEST", "Package manifest is empty or missing.", "/package/manifest")
    manifest_items: list[Element] = list(manifest) if manifest is not None else []
    for item in manifest_items:
        if item.tag != OPF + "item":
            continue
        identifier, href, media = (
            item.get("id", ""),
            item.get("href", ""),
            item.get("media-type", ""),
        )
        if not identifier or not href or not media:
            finding(
                "EPUB_MANIFEST", "Manifest item needs id, href and media-type.", "/package/manifest"
            )
            continue
        if identifier in items:
            finding("EPUB_MANIFEST_ID", "Manifest contains a duplicate id.", "/package/manifest")
            continue
        target = resolve_reference(package_path, href)
        if target is None:
            raise InputError("EPUB_REMOTE_RESOURCE", "Remote manifest resources are unsupported.")
        if target[1]:
            finding(
                "EPUB_MANIFEST", "Manifest href must not include a fragment.", "/package/manifest"
            )
        destination = target[0]
        if destination in destinations:
            finding(
                "EPUB_MANIFEST_PATH",
                "Manifest items resolve to a duplicate path.",
                "/package/manifest",
            )
        destinations.add(destination)
        items[identifier] = destination, media
        if destination not in contents:
            finding("EPUB_MISSING_RESOURCE", "Manifest resource is absent.", "/package/manifest")
        if "nav" in item.get("properties", "").split():
            nav_count += 1
    if nav_count != 1:
        finding("EPUB_NAV", "EPUB 3 must declare one navigation document.", "/package/manifest")
    spine = package.find(OPF + "spine")
    if spine is None or not list(spine):
        finding("EPUB_SPINE", "Reading-order spine is empty or missing.", "/package/spine")
    else:
        if spine.get("page-progression-direction", "default") not in {"rtl", "ltr", "default"}:
            finding("EPUB_SPINE_DIRECTION", "Invalid page progression direction.", "/package/spine")
        if language.split("-")[0].lower() == "fa" and not spine.get("page-progression-direction"):
            finding(
                "EPUB_SPINE_DIRECTION",
                "Persian package has no reading-direction declaration.",
                "/package/spine",
                True,
            )
        for itemref in spine:
            target_item = items.get(itemref.get("idref", ""))
            if target_item is None:
                finding(
                    "EPUB_SPINE_REFERENCE",
                    "Spine idref is absent from the manifest.",
                    "/package/spine",
                )
            elif target_item[1] not in {"application/xhtml+xml", "image/svg+xml"}:
                finding(
                    "EPUB_SPINE_TYPE",
                    "Spine item has an unsupported content media type.",
                    "/package/spine",
                )
    documents: dict[str, Document] = {}
    for destination, media in sorted(set(items.values())):
        if destination in contents and media == "application/xhtml+xml":
            documents[destination] = check_xhtml(
                contents[destination], path + "!/" + destination, report, limits, language
            )
    for source, document in sorted(documents.items()):
        for reference, location in document.references:
            target = resolve_reference(source, reference)
            if target is None:
                continue  # External links are never fetched.
            destination, fragment = target
            if destination not in contents:
                report.add(
                    Finding(
                        "EPUB_BROKEN_REFERENCE",
                        "error",
                        path + "!/" + source,
                        "Internal linked resource is absent.",
                        location,
                    )
                )
            elif (
                fragment and destination in documents and fragment not in documents[destination].ids
            ):
                report.add(
                    Finding(
                        "EPUB_BROKEN_FRAGMENT",
                        "error",
                        path + "!/" + source,
                        "Internal fragment target is absent.",
                        location,
                    )
                )
    return sum(len(value) for value in contents.values())
