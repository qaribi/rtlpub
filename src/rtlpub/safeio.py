"""Bounded filesystem, ZIP and XML reads. No extraction or network access."""

import io
import os
import stat
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree.ElementTree import Element, TreeBuilder
from xml.parsers import expat

from .models import InputError, Limits


def read_file(path: Path, maximum: int) -> bytes:
    if linked(path) or not path.is_file():
        raise InputError("INPUT_PATH", "Expected a regular file without symlinks.")
    with path.open("rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise InputError("INPUT_PATH", "Expected a regular file.")
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise InputError("INPUT_SIZE", "Input exceeds the byte budget.")
    return data


def linked(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def safe_member(name: str) -> str:
    parts = PurePosixPath(name).parts
    if (
        not name
        or "\\" in name
        or "\0" in name
        or name.startswith("/")
        or any(p in {"..", "."} or ":" in p for p in name.split("/"))
        or not parts
    ):
        raise InputError("ZIP_PATH", "Archive contains an unsafe member path.")
    return str(PurePosixPath(name))


def read_zip(data: bytes, limits: Limits) -> dict[str, bytes]:
    contents: dict[str, bytes] = {}
    if len(data) > limits.archive_bytes:
        raise InputError("ZIP_SIZE", "Archive exceeds the compressed byte budget.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > limits.files:
                raise InputError("ZIP_COUNT", "Archive exceeds the member count budget.")
            declared = 0
            seen: set[str] = set()
            for member in members:
                safe_member(member.orig_filename)
                name = safe_member(member.filename)
                if name in seen:
                    raise InputError("ZIP_DUPLICATE", "Archive contains duplicate member paths.")
                seen.add(name)
                mode = member.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if kind not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise InputError("ZIP_SPECIAL", "Archive contains a symlink or special file.")
                if member.flag_bits & 1:
                    raise InputError("EPUB_ENCRYPTED", "Encrypted archives are unsupported.")
                if member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                    raise InputError(
                        "ZIP_COMPRESSION", "Archive compression method is unsupported."
                    )
                if member.file_size > limits.file_bytes:
                    raise InputError("ZIP_SIZE", "Archive member exceeds the byte budget.")
                if member.is_dir() and member.file_size:
                    raise InputError("ZIP_DIRECTORY_PAYLOAD", "Archive directories must be empty.")
                declared += member.file_size
                if declared > limits.total_bytes:
                    raise InputError("ZIP_SIZE", "Archive exceeds the expanded byte budget.")
                if member.file_size > max(1, member.compress_size) * limits.zip_ratio:
                    raise InputError(
                        "ZIP_RATIO", "Archive member exceeds the compression ratio budget."
                    )
            actual = 0
            for member in members:
                with archive.open(member) as stream:
                    payload = stream.read(min(limits.file_bytes, limits.total_bytes - actual) + 1)
                actual += len(payload)
                if len(payload) != member.file_size or actual > limits.total_bytes:
                    raise InputError("ZIP_SIZE", "Expanded data violates the archive byte budget.")
                if not member.is_dir():
                    contents[safe_member(member.filename)] = payload
            if members and (
                members[0].filename != "mimetype" or members[0].compress_type != zipfile.ZIP_STORED
            ):
                raise InputError("EPUB_MIMETYPE", "EPUB mimetype must be first and uncompressed.")
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError) as exc:
        raise InputError("ZIP_INVALID", "Archive cannot be safely read.") from exc
    return contents


def parse_xml(data: bytes, limits: Limits) -> Element:
    builder = TreeBuilder()
    parser = expat.ParserCreate(namespace_separator="}")
    depth = 0
    nodes = 0

    def expanded(name: str) -> str:
        return "{" + name if "}" in name else name

    def start(name: str, attributes: dict[str, str]) -> None:
        nonlocal depth, nodes
        depth += 1
        nodes += 1
        if depth > limits.xml_depth or nodes > limits.xml_nodes:
            raise InputError("XML_LIMIT", "XML exceeds the structure budget.")
        builder.start(expanded(name), {expanded(k): v for k, v in attributes.items()})

    def end(name: str) -> None:
        nonlocal depth
        builder.end(expanded(name))
        depth -= 1

    def forbid(*arguments: object) -> None:
        raise InputError("XML_UNSAFE", "DTD and entity declarations are unsupported.")

    def reject_external(*arguments: object) -> int:
        raise InputError("XML_UNSAFE", "External XML entities are unsupported.")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = builder.data
    parser.StartDoctypeDeclHandler = forbid
    parser.EntityDeclHandler = forbid
    parser.ExternalEntityRefHandler = reject_external
    try:
        parser.Parse(data, True)
        return builder.close()
    except (expat.ExpatError, ValueError) as exc:
        raise InputError("XML_INVALID", "XML is malformed or has an unsupported encoding.") from exc
