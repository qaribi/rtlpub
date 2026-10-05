# Source and example provenance

This project's code, tests and examples were newly authored for this repository
from general publishing requirements. No application source, book assets, private
history or copied calendar implementation is included. Synthetic text and EPUB
fixtures are covered by the repository MIT license.

The runtime uses Python's standard library only. Python remains separately
licensed by its distributors; it is not bundled. No third-party code or validator
binaries are vendored. Setuptools is the build backend; Ruff and Pyright are
development tools with their own upstream licenses. GitHub Actions are referenced
by commit, not distributed as project source.

References informing the checks:

- [EPUB 3.3](https://www.w3.org/TR/epub-33/).
- [Unicode Bidirectional Algorithm](https://www.unicode.org/reports/tr9/).
- [Python XML security](https://docs.python.org/3/library/xml.html).
- [EPUBCheck](https://github.com/w3c/epubcheck) and [Ace](https://github.com/daisy/ace).

References are not endorsements and the tool does not certify their full standards.
