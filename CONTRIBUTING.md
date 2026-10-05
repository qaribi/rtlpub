# Contributing

Use a supported Python in a virtual environment. Install the checkout, run
python -m unittest discover -v, Ruff checks/format checks and Pyright.
CI supplies the pinned development-tool versions.

Open an issue with the rule ID, expected result and a small synthetic example.
Never upload a copyrighted/private book, credentials or personal information.
For bugs, add a regression test that fails before the change and passes after it.
Keep language/direction false positives and report compatibility in mind.

Pull requests should explain the user-visible change, limitations and verification.
Changes must retain offline operation, bounded reads and read-only defaults.
By contributing you confirm the right to license your contribution under MIT.
Security reports follow SECURITY.md; external inputs are untrusted.
Maintainers review changes and decide merges/releases manually.
