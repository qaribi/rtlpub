# Rules

Text warnings: TEXT_ARABIC_LETTER (only Persian-language text),
TEXT_BIDI_CONTROL, TEXT_ZWNJ_BOUNDARY, TEXT_EMBEDDED_BOM, TEXT_NON_NFC.
They flag review points, not definitive language mistakes. Controls can be valid.

XHTML warnings: XHTML_LANGUAGE, XHTML_DIRECTION, XHTML_LANG_CONFLICT,
XHTML_ALT, XHTML_HEADING, XHTML_EFFECTIVE_DIRECTION. The last rule advises review
of Persian text nodes containing at least twelve RTL strong characters under
effective LTR; it is not a blanket error on LTR markup. bdi defaults to auto.
Empty alt is accepted; quality of nonempty alt is
not judged. Duplicate IDs and invalid direction values are errors:
XHTML_DUPLICATE_ID, XHTML_DIR_VALUE.

EPUB package errors: EPUB_METADATA, EPUB_IDENTIFIER, EPUB_MANIFEST,
EPUB_MANIFEST_ID, EPUB_MANIFEST_PATH, EPUB_MISSING_RESOURCE, EPUB_NAV,
EPUB_SPINE, EPUB_SPINE_REFERENCE, EPUB_SPINE_TYPE,
EPUB_BROKEN_REFERENCE, EPUB_BROKEN_FRAGMENT.
Missing Persian spine direction warns with EPUB_SPINE_DIRECTION; invalid values
are errors. Only declared XHTML documents receive content/reference checks.

INPUT_*, ZIP_*, XML_* and unsupported EPUB conditions set invalid input
and exit 2 independently of the selected finding threshold. Encryption including
font obfuscation, multiple package rootfiles and remote manifest resources are
unsupported; ordinary external hyperlinks are ignored without fetching.

Limits are fixed in CLI; the Python Limits dataclass permits smaller budgets
for embedding/tests. This is not a complete catalog of EPUB normative requirements.
