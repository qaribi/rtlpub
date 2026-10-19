"""Synthetic, offline language-tag regressions (RFC 5646 sections 2.1 and 2.2.9)."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rtlpub import Limits, check_path
from rtlpub.cli import main
from rtlpub.epub import check_epub
from rtlpub.language import is_well_formed_language_tag
from rtlpub.models import Report
from rtlpub.xhtml import check_xhtml

from .helpers import CHAPTER, PACKAGE, epub

VALID = (
    "fa",
    "fa-IR",
    "ar",
    "prs",
    "ps-AF",
    "ur-PK",
    "en",
    "FA-ir",
    "sr-Latn-RS",
    "zh-cmn-Hans-CN",
    "es-419",
    "de-CH-1901",
    "sl-rozaj-biske-1994",
    "en-US-u-ca-gregory",
    "en-a-aaa-b-bbb-x-private",
    "x-local",
    "i-klingon",
    "en-GB-oed",
    "sgn-BE-FR",
    "zh-min-nan",
    "en-0-abc",
    "en-x-a-a",
    "qaa-Qaaa-QM",
    "abcd",
    "abcdefgh",
    "en-1234",
    "en-abc-def-ghi",
    "und",
    "zxx",
)
INVALID = (
    "fa_IR",
    "fa--IR",
    "-fa",
    "fa-",
    "f",
    "123",
    "en-ab12",
    "en-abcdefghi",
    "en-Latn-Latn",
    "en-US-GB",
    "en-u",
    "en-x",
    "x",
    "en-a-b-foo",
    "en-a-foo-A-bar",
    "sl-rozaj-ROZAJ",
    "fa IR",
    "fa,ar",
    "fa@IR",
    "fa.utf8",
    "fа",
    "en-۱۲۳",
    "en-abc-def-ghi-jkl",
    "i-madeup",
    " fa",
    "fa ",
    "fa\n",
    "en-*-US",
)


class LanguageTests(unittest.TestCase):
    def test_shared_parser_boundaries(self) -> None:
        for tag in VALID:
            with self.subTest(tag=tag):
                self.assertTrue(is_well_formed_language_tag(tag))
        for tag in (*INVALID, "", "en\x00", "fa\tIR"):
            with self.subTest(tag=tag):
                self.assertFalse(is_well_formed_language_tag(tag))
        # No invented maximum tag length and no recursive/backtracking parser.
        self.assertTrue(is_well_formed_language_tag("en-x" + "-abcdefgh" * 10000))
        self.assertFalse(is_well_formed_language_tag("en" + "-abcde" * 10000))

    def test_all_grandfathered_tags(self) -> None:
        tags = """en-GB-oed i-ami i-bnn i-default i-enochian i-hak i-klingon
        i-lux i-mingo i-navajo i-pwn i-tao i-tay i-tsu sgn-BE-FR sgn-BE-NL
        sgn-CH-DE art-lojban cel-gaulish no-bok no-nyn zh-guoyu zh-hakka
        zh-min zh-min-nan zh-xiang""".split()
        self.assertEqual(len(tags), 26)
        for tag in tags:
            with self.subTest(tag=tag):
                self.assertTrue(is_well_formed_language_tag(tag.upper()))

    def xhtml(self, attributes: str, body: str = "") -> Report:
        report = Report()
        data = f'<html xmlns="http://www.w3.org/1999/xhtml" {attributes}><body>{body}</body></html>'
        check_xhtml(data.encode(), "sample.xhtml", report, Limits())
        return report

    def test_valid_structures_in_xhtml_and_epub(self) -> None:
        for tag in VALID:
            with self.subTest(tag=tag):
                for attribute in ("lang", "xml:lang"):
                    report = self.xhtml(f'{attribute}="{tag}" dir="rtl"')
                    self.assertEqual(report.findings, [])
                report = Report()
                package = PACKAGE.replace(
                    "<dc:language>fa</dc:language>", f"<dc:language>{tag}</dc:language>"
                )
                check_epub(
                    epub({"EPUB/package.opf": package.encode()}), "book.epub", report, Limits()
                )
                self.assertEqual(report.findings, [])

    def test_invalid_structures_in_each_xhtml_attribute(self) -> None:
        for tag in INVALID:
            for attribute in ("lang", "xml:lang"):
                with self.subTest(tag=tag, attribute=attribute):
                    # XML attribute whitespace normalization is deliberate.
                    report = self.xhtml(f'{attribute}="{tag}" dir="rtl"')
                    errors = [f for f in report.findings if f.rule == "XHTML_LANGUAGE_TAG"]
                    self.assertEqual(len(errors), 1)
                    self.assertEqual(errors[0].severity, "error")
                    self.assertEqual(errors[0].location, f"/html/@{attribute}")
                    self.assertFalse(report.invalid_input)

    def test_every_metadata_language_is_checked(self) -> None:
        for tag in INVALID:
            if tag != tag.strip():
                continue  # OPF element content is stripped as for other metadata.
            with self.subTest(tag=tag):
                package = PACKAGE.replace(
                    "</dc:language>", f"</dc:language><dc:language>{tag}</dc:language>", 1
                )
                report = Report()
                check_epub(
                    epub({"EPUB/package.opf": package.encode()}), "book.epub", report, Limits()
                )
                errors = [f for f in report.findings if f.rule == "EPUB_LANGUAGE_TAG"]
                self.assertEqual(len(errors), 1)
                self.assertEqual(errors[0].location, "/package/metadata/dc:language[2]")
                self.assertEqual(errors[0].severity, "error")

    def test_overridden_attribute_and_nested_declarations_are_checked(self) -> None:
        report = self.xhtml(
            'lang="fa_IR" xml:lang="fa" dir="rtl"',
            '<p lang="en"><span xml:lang="ur_PK"/></p>',
        )
        self.assertEqual(
            {f.location for f in report.findings if f.rule == "XHTML_LANGUAGE_TAG"},
            {"/html/@lang", "/html/body[1]/p[1]/span[1]/@xml:lang"},
        )
        self.assertEqual(
            [f.severity for f in report.findings if f.rule == "XHTML_LANG_CONFLICT"], ["warning"]
        )
        self.assertEqual(self.xhtml('lang="FA-ir" xml:lang="fa-IR" dir="rtl"').findings, [])

    def test_empty_xhtml_means_unknown_language(self) -> None:
        report = self.xhtml('lang="" xml:lang=""', '<p lang="" xml:lang=""/>')
        self.assertEqual([f.rule for f in report.findings], ["XHTML_LANGUAGE"])
        report = self.xhtml('lang="fa" dir="rtl"', '<p lang="" xml:lang="">كتاب</p>')
        self.assertEqual(report.findings, [])

    def test_empty_metadata_and_existing_missing_rule(self) -> None:
        for value in ("", " "):
            package = PACKAGE.replace("<dc:language>fa", f"<dc:language>{value}")
            report = Report()
            check_epub(epub({"EPUB/package.opf": package.encode()}), "book.epub", report, Limits())
            self.assertIn("EPUB_METADATA", {f.rule for f in report.findings})
            self.assertIn("EPUB_LANGUAGE_TAG", {f.rule for f in report.findings})

    def test_cli_json_read_only_offline_and_error_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            for suffix, payload in (
                ("xhtml", CHAPTER.replace('lang="fa"', 'lang="fa_IR"', 1).encode()),
                (
                    "epub",
                    epub(
                        {
                            "EPUB/package.opf": PACKAGE.replace(
                                "<dc:language>fa", "<dc:language>fa_IR"
                            ).encode()
                        }
                    ),
                ),
            ):
                path = Path(folder) / f"sample.{suffix}"
                path.write_bytes(payload)
                runs = []
                with patch("socket.socket", side_effect=AssertionError("Network forbidden")):
                    for _ in range(2):
                        output = io.StringIO()
                        with contextlib.redirect_stdout(output):
                            code = main(["check", str(path), "--format", "json"])
                        self.assertEqual(code, 1)
                        runs.append(output.getvalue())
                    self.assertEqual(check_path(path).exit_code(), 1)
                self.assertEqual(runs[0], runs[1])
                result = json.loads(runs[0])
                self.assertEqual(result["schema_version"], "1.0")
                self.assertEqual(result["status"], "checked")
                self.assertNotIn("fa_IR", runs[0])
                self.assertEqual(path.read_bytes(), payload)

    def test_conflict_remains_advisory(self) -> None:
        report = self.xhtml('lang="fa" xml:lang="ar" dir="rtl"')
        self.assertEqual(report.exit_code(), 0)
        self.assertEqual(report.exit_code("warning"), 1)
