# Security

This checker reads untrusted ZIP/XML/text; run it with a supported, patched Python,
as an unprivileged user with ordinary OS resource restrictions. It does not render
HTML, execute scripts, extract archives, decrypt content or fetch external URLs.
Parsing accepts XML with no DTD/entity declarations, including UTF-16 inputs.
Budgets cover every ZIP member, actual expanded bytes, structure and findings.
Symlinks and junctions are unsupported.

The checker is not a sandbox, full security scanner or guarantee against every
parser/runtime vulnerability. Concurrent hostile filesystem changes are outside
the threat model; check a stable input tree. Do not run on a writable adversary-
controlled live tree or with privileged credentials. Filenames are included in
reports; book text and raw exception details are not.

For a suspected vulnerability, use GitHub's private vulnerability reporting on
this repository if enabled. If unavailable, open a public issue requesting a
private reporting channel **without** exploit details, sensitive files or secrets.
Do not post an exploit or a private book in a public issue.
Only the current release is supported initially; response timing is not guaranteed.
Fixes will receive regression tests and release notes. No paid LLM security
automation, self-hosted runner or automatic privileged merge is active.
