# CLI/report contract

rtlpub check PATH [--format human|json] [--fail-on error|warning|info]
[--text-language fa|ar|und]

PATH is one supported file or a directory. Extension matching is case insensitive:
.txt, .xhtml, .html (XML XHTML only), .epub. Unsupported directory files
are skipped; every directory entry counts toward the entry budget. A directory
with no supported files is invalid. Symlinks/junctions anywhere in the input path
or tree are rejected, even if their extensions are unsupported.

Exit 0: no finding reaches threshold. Exit 1: one or more findings reach it.
Exit 2: input unsupported/unreadable/invalid, budget exhausted, or processing failed.
Default threshold error permits warnings. CLI argument errors also exit 2.

JSON object:

- schema_version: "1.0"; tool_version: semantic package version.
- threshold, exit_code, checked_files.
- status: "checked" or "invalid_input"; checked is not a conformance claim.
- findings: ordered array of rule, severity, path, message, location,
  line, column; unavailable locations are null.

Paths are relative to the requested directory, or the basename for a single file.
EPUB member paths use book.epub!/EPUB/chapter.xhtml. XML locations are structural
element paths, not source byte offsets. Plain text lines/columns are one-based
Unicode code points. Messages never quote input text, IDs or raw exceptions.
Finding order is deterministic. No timing, machine root or raw traceback is included.
Human output quotes paths to escape terminal control characters.

These are conservative authoring hints. XHTML language is inherited; xml:lang
precedes lang, conflicting declarations warn. Explicit direction values and
mixed spans are allowed. Missing root direction only warns for Persian roots.
CSS direction/style semantics are not inferred. No text is normalized.
