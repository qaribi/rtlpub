"""Offline BCP 47 structural checks, not IANA registry or canonicalization checks.

Implements RFC 5646 section 2.1 grammar and the duplicate variant/singleton
constraints of section 2.2.9. Work and storage are linear in the input size;
callers already bound XML sizes. Never normalize or echo publication data.
"""

# RFC 5646's fixed grandfathered set includes irregular and regular tags.
_GRANDFATHERED = frozenset(
    """en-GB-oed i-ami i-bnn i-default i-enochian i-hak i-klingon i-lux
    i-mingo i-navajo i-pwn i-tao i-tay i-tsu sgn-BE-FR sgn-BE-NL sgn-CH-DE
    art-lojban cel-gaulish no-bok no-nyn zh-guoyu zh-hakka zh-min zh-min-nan
    zh-xiang""".lower().split()
)


def is_well_formed_language_tag(value: str) -> bool:
    """Accept structural tags for any language, regardless of case or registration.

    Empty values are not tags; XHTML callers separately allow the empty-string
    unknown-language declaration. Private-use payloads are opaque, including
    repeated subtags. Extension-specific semantics are deliberately not checked.
    """
    if not value or not value.isascii():
        return False
    tag = value.lower()
    if tag in _GRANDFATHERED:
        return True
    parts = tag.split("-")
    if any(not (1 <= len(part) <= 8 and part.isalnum()) for part in parts):
        return False
    if parts[0] == "x":
        return len(parts) > 1
    first = parts[0]
    if not (2 <= len(first) <= 8 and first.isalpha()):
        return False
    index = 1
    # Extlang is available only after a two- or three-letter primary language.
    if len(first) <= 3:
        for _ in range(3):
            if index < len(parts) and len(parts[index]) == 3 and parts[index].isalpha():
                index += 1
            else:
                break
    if index < len(parts) and len(parts[index]) == 4 and parts[index].isalpha():
        index += 1  # Script
    if index < len(parts) and (
        (len(parts[index]) == 2 and parts[index].isalpha())
        or (len(parts[index]) == 3 and parts[index].isdigit())
    ):
        index += 1  # Region
    variants: set[str] = set()
    while index < len(parts):
        part = parts[index]
        if not (5 <= len(part) <= 8 or (len(part) == 4 and part[0].isdigit())):
            break
        if part in variants:
            return False
        variants.add(part)
        index += 1
    singletons: set[str] = set()
    while index < len(parts) and len(parts[index]) == 1 and parts[index] != "x":
        singleton = parts[index]
        if singleton in singletons:
            return False
        singletons.add(singleton)
        index += 1
        start = index
        while index < len(parts) and len(parts[index]) >= 2:
            index += 1
        if index == start:
            return False
    if index < len(parts) and parts[index] == "x":
        return index + 1 < len(parts)  # All remaining 1..8 alphanumeric parts are private.
    return index == len(parts)
