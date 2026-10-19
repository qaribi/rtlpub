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

## Language tags

`XHTML_LANGUAGE_TAG` and `EPUB_LANGUAGE_TAG` are **errors** for definite structural
failures. The shared offline parser follows [RFC 5646 section 2.1 and section
2.2.9](https://www.rfc-editor.org/rfc/rfc5646.html): ASCII subtags separated by
hyphens, primary language, up to three extlangs where permitted, optional script
and region, variants, extensions and private use. Repeated variants or extension
singletons (case-insensitive) are errors. Private-use repetitions are allowed.
The fixed set of 26 grandfathered tags is accepted. There is no language allowlist,
network lookup, runtime dependency, automatic correction or arbitrary tag-length
cutoff beyond existing input budgets. Parsing is linear in tag length.

Examples accepted structurally: `fa`, `fa-IR`, `ar`, `prs`, `ps-AF`, `ur-PK`,
`sr-Latn-RS`, `es-419`, `zh-cmn-Hans-CN`, `sl-rozaj-biske-1994`,
`en-US-u-ca-gregory`, `x-local`, `i-klingon`. Case alone is never an error.
Examples rejected: `fa_IR` (use `fa-IR`), `fa--IR`, `en-u`, `en-x`,
`en-a-foo-A-bar`, `sl-rozaj-ROZAJ`, spaces and non-ASCII characters.

All explicit XHTML `lang` and `xml:lang` attributes, including descendants and
attributes overridden by `xml:lang`, are checked independently. Locations include
`/@lang` or `/@xml:lang`. An exactly empty XHTML value is allowed: it declares an
unknown language and stops inheritance. Missing/empty root language continues to
warn with `XHTML_LANGUAGE`; differing attributes continue to warn with
`XHTML_LANG_CONFLICT`. These warnings are review points, not structural errors.
Every `dc:language` in package metadata is checked, with a one-based location such
as `/package/metadata/dc:language[2]`. OPF text is stripped of surrounding whitespace
as before; an empty metadata value is an error. Missing/all-empty language metadata
also retains `EPUB_METADATA`. XHTML attribute values are checked after XML parsing,
without additional trimming. XML's own attribute normalization still applies.

Well-formed does **not** mean registered or semantically correct. No IANA registry
is bundled or queried; registry membership, extlang/variant prefix constraints,
deprecation, canonicalization and extension-specific rules are outside scope.
For example a structurally possible unregistered subtag is accepted, not guessed
invalid. No warning is emitted merely because registration is unknown.
Text-language/direction heuristics and EPUB fallback precedence are unchanged.
New findings use the existing JSON schema 1.0 and finding fields; structural errors
exit 1 at the default threshold, not invalid-input exit 2. Finding caps, bounded
reads, safe XML/ZIP handling, offline operation and read-only inputs still apply.
