"""Create a synthetic EPUB; refuses overwrite and never uses real book content."""

import argparse
import zipfile
from pathlib import Path

CONTAINER = """<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="EPUB/package.opf"
media-type="application/oebps-package+xml"/></rootfiles></container>"""
PACKAGE = """<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="sample">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Synthetic RTL example</dc:title>
<dc:identifier id="sample">urn:example:rtlpub</dc:identifier><dc:language>fa</dc:language>
<meta property="dcterms:modified">2026-10-05T00:00:00Z</meta></metadata>
<manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest>
<spine page-progression-direction="rtl"><itemref idref="chapter"/></spine></package>"""
NAV = """<html xmlns="http://www.w3.org/1999/xhtml" lang="fa" dir="rtl"
xmlns:epub="http://www.idpf.org/2007/ops"><head><title>فهرست</title></head><body>
<nav epub:type="toc"><h1>فهرست</h1><ol><li><a href="chapter.xhtml#start">نمونه</a>
</li></ol></nav></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    destination = parser.parse_args().destination
    with destination.open("xb") as output, zipfile.ZipFile(output, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", CONTAINER)
        archive.writestr("EPUB/package.opf", PACKAGE)
        archive.writestr(
            "EPUB/chapter.xhtml", Path(__file__).with_name("persian.xhtml").read_bytes()
        )
        archive.writestr("EPUB/nav.xhtml", NAV)


if __name__ == "__main__":
    main()
