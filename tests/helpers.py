"""Synthetic publications written for these tests; no real book content."""

import io
import zipfile

CONTAINER = b"""<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="EPUB/package.opf"
media-type="application/oebps-package+xml"/></rootfiles></container>"""
PACKAGE = """<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Synthetic sample</dc:title>
<dc:identifier id="book">urn:example:rtlpub-test</dc:identifier>
<dc:language>fa</dc:language></metadata>
<manifest><item id="chapter" href="text/chapter.xhtml" media-type="application/xhtml+xml"/>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest>
<spine page-progression-direction="rtl"><itemref idref="chapter"/></spine></package>"""
CHAPTER = """<html xmlns="http://www.w3.org/1999/xhtml" lang="fa" dir="rtl">
<head><title>نمونه</title></head><body><h1 id="start">نمونهٔ تازه</h1>
<p>کتاب‌ها برای خواندن‌اند.</p><span lang="en" dir="ltr">Open example 12</span>
<p lang="ar">كتاب عربي</p><bdi dir="auto">mixed 123</bdi>
</body></html>"""
NAV = """<html xmlns="http://www.w3.org/1999/xhtml" lang="fa" dir="rtl"
xmlns:epub="http://www.idpf.org/2007/ops"><head><title>فهرست</title></head><body>
<nav epub:type="toc"><h1>فهرست</h1><ol><li><a href="text/chapter.xhtml#start">نمونه</a>
</li></ol></nav></body></html>"""


def epub(overrides: dict[str, bytes] | None = None, compression: int = zipfile.ZIP_STORED) -> bytes:
    members = {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": CONTAINER,
        "EPUB/package.opf": PACKAGE.encode(),
        "EPUB/text/chapter.xhtml": CHAPTER.encode(),
        "EPUB/nav.xhtml": NAV.encode(),
    }
    members.update(overrides or {})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        for name, payload in members.items():
            archive.writestr(
                name,
                payload,
                compress_type=zipfile.ZIP_STORED if name == "mimetype" else compression,
            )
    return buffer.getvalue()
