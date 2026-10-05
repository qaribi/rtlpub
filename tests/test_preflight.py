import contextlib
import io
import json
import os
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

from rtlpub import Limits, check_path
from rtlpub.cli import main
from rtlpub.epub import resolve_reference
from rtlpub.models import InputError, Report
from rtlpub.safeio import parse_xml, read_zip
from rtlpub.text import check_text
from rtlpub.xhtml import check_xhtml

from .helpers import CHAPTER, NAV, PACKAGE, epub


class PreflightTests(unittest.TestCase):
    def xhtml(self, text: str) -> Report:
        report = Report()
        check_xhtml(text.encode(), "sample.xhtml", report, Limits())
        return report

    def codes(self, report: Report) -> set[str]:
        return {finding.rule for finding in report.findings}

    def test_synthetic_publication_passes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.epub"
            path.write_bytes(epub())
            report = check_path(path)
            self.assertEqual(report.to_dict()["findings"], [])
            self.assertEqual(report.exit_code(), 0)

    def test_inherited_language_and_direction(self) -> None:
        self.assertEqual(self.xhtml(CHAPTER).findings, [])

    def test_explicit_arabic_quote_is_not_normalized(self) -> None:
        self.assertNotIn("TEXT_ARABIC_LETTER", self.codes(self.xhtml(CHAPTER)))

    def test_mixed_ltr_and_auto_are_allowed(self) -> None:
        report = self.xhtml(CHAPTER.replace("Open example 12", "فارسی"))
        self.assertEqual(report.findings, [])

    def test_effective_ltr_persian_text_is_advisory(self) -> None:
        report = self.xhtml(CHAPTER.replace('dir="rtl"', 'dir="ltr"', 1))
        self.assertIn("XHTML_EFFECTIVE_DIRECTION", self.codes(report))
        self.assertEqual(report.exit_code(), 0)
        self.assertEqual(report.exit_code("warning"), 1)

    def test_bdi_defaults_to_auto_and_explicit_auto_allowed(self) -> None:
        text = "این متن فارسی برای بررسی جهت نوشته شده است"
        for markup in (f"<bdi>{text}</bdi>", f'<p dir="auto">{text}</p>'):
            document = CHAPTER.replace('dir="rtl"', 'dir="ltr"', 1)
            document = document.replace("کتاب‌ها برای خواندن‌اند.", "short")
            document = document.replace("</body>", markup + "</body>")
            self.assertNotIn("XHTML_EFFECTIVE_DIRECTION", self.codes(self.xhtml(document)))

    def test_arabic_letters_are_only_advisory(self) -> None:
        report = self.xhtml(CHAPTER.replace("کتاب‌ها", "كتاب‌ها"))
        self.assertIn("TEXT_ARABIC_LETTER", self.codes(report))
        self.assertEqual(report.exit_code(), 0)
        self.assertEqual(report.exit_code("warning"), 1)

    def test_decorative_empty_alt_allowed(self) -> None:
        self.assertNotIn(
            "XHTML_ALT",
            self.codes(
                self.xhtml(CHAPTER.replace("</body>", '<img src="image.png" alt=""/></body>'))
            ),
        )

    def test_missing_alt_and_heading_jump(self) -> None:
        report = self.xhtml(CHAPTER.replace("</body>", "<h3>Heading</h3><img/></body>"))
        self.assertTrue({"XHTML_ALT", "XHTML_HEADING"} <= self.codes(report))

    def test_invalid_direction_and_duplicate_ids(self) -> None:
        report = self.xhtml(CHAPTER.replace("</body>", '<p id="start" dir="sideways"/></body>'))
        self.assertTrue({"XHTML_DIR_VALUE", "XHTML_DUPLICATE_ID"} <= self.codes(report))
        self.assertEqual(report.exit_code(), 1)

    def test_lang_disagreement(self) -> None:
        self.assertIn(
            "XHTML_LANG_CONFLICT",
            self.codes(self.xhtml(CHAPTER.replace('lang="fa"', 'lang="fa" xml:lang="ar"', 1))),
        )

    def test_plain_text_locations_and_no_excerpt(self) -> None:
        report = Report()
        check_text("synthetic-private-marker\nي\u202e\u200c ", "sample.txt", report)
        self.assertEqual(report.findings[0].line, 2)
        self.assertEqual(report.findings[0].column, 1)
        self.assertNotIn("synthetic-private-marker", json.dumps(report.to_dict()))
        self.assertTrue(
            {"TEXT_ARABIC_LETTER", "TEXT_BIDI_CONTROL", "TEXT_ZWNJ_BOUNDARY"} <= self.codes(report)
        )

    def test_normalization_is_never_applied(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.txt"
            original = "ي ك \u200c e\u0301 ۱۲٣".encode()
            path.write_bytes(original)
            report = check_path(path)
            self.assertIn("TEXT_NON_NFC", self.codes(report))
            self.assertEqual(path.read_bytes(), original)

    def test_arabic_plain_text_mode(self) -> None:
        report = Report()
        check_text("كتاب عربي", "sample.txt", report, "ar")
        self.assertEqual(report.findings, [])

    def test_entities_and_dtd_rejected_in_both_encodings(self) -> None:
        attacks = [
            '<!DOCTYPE html [<!ENTITY x "synthetic">]><html>&x;</html>',
            '<!DOCTYPE html SYSTEM "https://example.invalid/external"><html/>',
        ]
        for attack in attacks:
            for encoding in ("utf-8", "utf-16"):
                with self.subTest(attack=attack[:15], encoding=encoding):
                    with self.assertRaises(InputError) as caught:
                        parse_xml(attack.encode(encoding), Limits())
                    self.assertEqual(caught.exception.rule, "XML_UNSAFE")

    def test_xml_depth_and_node_budgets(self) -> None:
        for xml, limits in [
            (b"<a><a><a/></a></a>", Limits(xml_depth=2)),
            (b"<a><b/><c/></a>", Limits(xml_nodes=2)),
        ]:
            with self.assertRaises(InputError) as caught:
                parse_xml(xml, limits)
            self.assertEqual(caught.exception.rule, "XML_LIMIT")

    def test_malformed_xml_controlled(self) -> None:
        with self.assertRaises(InputError):
            parse_xml(b"<html><broken>", Limits())

    def test_parent_and_percent_encoded_links(self) -> None:
        self.assertEqual(
            resolve_reference("EPUB/text/chapter.xhtml", "../nav.xhtml"), ("EPUB/nav.xhtml", "")
        )
        self.assertEqual(
            resolve_reference("EPUB/nav.xhtml", "text/chapter.xhtml#%73tart"),
            ("EPUB/text/chapter.xhtml", "start"),
        )

    def test_reference_traversal_and_bad_percent(self) -> None:
        for href in ("../../../../outside", "%2e%2e/%2e%2e/out", "/absolute", "file%5cname", "%FF"):
            with self.subTest(href=href), self.assertRaises(InputError):
                resolve_reference("EPUB/nav.xhtml", href)

    def test_external_reference_never_resolved(self) -> None:
        self.assertIsNone(resolve_reference("chapter.xhtml", "https://example.invalid/never-fetch"))

    def test_metadata_manifest_spine_failures(self) -> None:
        broken = PACKAGE.replace("<dc:title>Synthetic sample</dc:title>", "")
        broken = broken.replace('idref="chapter"', 'idref="missing"')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.epub"
            path.write_bytes(epub({"EPUB/package.opf": broken.encode()}))
            report = check_path(path)
            self.assertTrue({"EPUB_METADATA", "EPUB_SPINE_REFERENCE"} <= self.codes(report))
            self.assertEqual(report.exit_code(), 1)

    def test_missing_resource_and_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.epub"
            path.write_bytes(
                epub(
                    {
                        "EPUB/nav.xhtml": NAV.replace("#start", "#missing")
                        .replace("</body>", '<img src="missing.png" alt=""/></body>')
                        .encode()
                    }
                )
            )
            self.assertTrue(
                {"EPUB_BROKEN_REFERENCE", "EPUB_BROKEN_FRAGMENT"} <= self.codes(check_path(path))
            )

    def test_encrypted_epub_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "encrypted.epub"
            path.write_bytes(epub({"META-INF/encryption.xml": b"<encryption/>"}))
            report = check_path(path)
            self.assertEqual(report.exit_code(), 2)
            self.assertIn("EPUB_ENCRYPTED", self.codes(report))

    def test_zip_traversal_rejected_without_extraction(self) -> None:
        for name in ("../outside", "/absolute", "C:/absolute"):
            with self.subTest(name=name), self.assertRaises(InputError):
                read_zip(epub({name: b"synthetic"}), Limits())

    def test_zip_backslash_path_rejected(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            member = zipfile.ZipInfo("safe")
            member.filename = "a\\b"
            archive.writestr(member, b"synthetic")
        with self.assertRaises(InputError) as caught:
            read_zip(buffer.getvalue(), Limits())
        self.assertEqual(caught.exception.rule, "ZIP_PATH")

    def test_zip_symlink_rejected(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            link = zipfile.ZipInfo("link")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(link, "../outside")
        with self.assertRaises(InputError) as caught:
            read_zip(buffer.getvalue(), Limits())
        self.assertEqual(caught.exception.rule, "ZIP_SPECIAL")

    def test_duplicate_zip_members_rejected(self) -> None:
        buffer = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("same", "one")
                archive.writestr("same", "two")
        with self.assertRaises(InputError) as caught:
            read_zip(buffer.getvalue(), Limits())
        self.assertEqual(caught.exception.rule, "ZIP_DUPLICATE")

    def test_nontext_members_consume_expanded_budget(self) -> None:
        data = epub({"large.bin": bytes(range(256)) * 10})
        with self.assertRaises(InputError) as caught:
            read_zip(data, Limits(total_bytes=2000))
        self.assertEqual(caught.exception.rule, "ZIP_SIZE")

    def test_zip_directory_payload_is_rejected(self) -> None:
        with self.assertRaises(InputError) as caught:
            read_zip(epub({"directory/": b"synthetic"}), Limits())
        self.assertEqual(caught.exception.rule, "ZIP_DIRECTORY_PAYLOAD")

    def test_zip_count_file_size_and_compression_ratio(self) -> None:
        probes = [
            (epub(), Limits(files=2), "ZIP_COUNT"),
            (epub(), Limits(file_bytes=10), "ZIP_SIZE"),
            (epub({"large.bin": b"x" * 10000}, zipfile.ZIP_DEFLATED), Limits(), "ZIP_RATIO"),
        ]
        for data, limits, code in probes:
            with self.subTest(code=code), self.assertRaises(InputError) as caught:
                read_zip(data, limits)
            self.assertEqual(caught.exception.rule, code)

    def test_invalid_zip_is_controlled(self) -> None:
        with self.assertRaises(InputError) as caught:
            read_zip(b"not a zip", Limits())
        self.assertEqual(caught.exception.rule, "ZIP_INVALID")

    def test_directory_filter_sort_and_budget(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "b.txt").write_text("ي", encoding="utf-8")
            (Path(folder) / "a.txt").write_text("ك", encoding="utf-8")
            (Path(folder) / "ignore.bin").write_bytes(b"ignored")
            report = check_path(folder)
            self.assertEqual(report.checked_files, 2)
            self.assertEqual(report.to_dict()["findings"][0]["path"], "a.txt")
            self.assertEqual(check_path(folder, Limits(files=1)).exit_code(), 2)

    def test_missing_unsupported_empty_and_size_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(check_path(root).exit_code(), 2)
            self.assertEqual(check_path(root / "missing.txt").exit_code(), 2)
            (root / "file.pdf").write_bytes(b"synthetic")
            self.assertEqual(check_path(root / "file.pdf").exit_code(), 2)
            (root / "large.txt").write_bytes(b"12345")
            self.assertEqual(check_path(root / "large.txt", Limits(file_bytes=4)).exit_code(), 2)

    def test_symlink_file_and_directory_escape(self) -> None:
        if os.name == "nt":
            self.skipTest("Windows symlink privilege is not assumed; Linux CI executes this probe")
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            root = Path(folder)
            target = Path(outside) / "external.txt"
            target.write_text("synthetic", encoding="utf-8")
            (root / "link.txt").symlink_to(target)
            (root / "subdirectory").symlink_to(outside, target_is_directory=True)
            self.assertEqual(check_path(root).exit_code(), 2)
            self.assertEqual(check_path(root / "link.txt").exit_code(), 2)

    def test_cli_json_stability_and_exit_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.txt"
            path.write_text("ي", encoding="utf-8")
            runs = []
            for _ in range(2):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(["check", str(path), "--format", "json", "--fail-on", "warning"])
                self.assertEqual(code, 1)
                runs.append(output.getvalue())
            self.assertEqual(runs[0], runs[1])
            self.assertEqual(json.loads(runs[0])["schema_version"], "1.0")

    def test_cli_human_path_escapes_bidi_controls(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample\u202e\u2066.txt"
            path.write_text("ي", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["check", str(path)])
            self.assertEqual(code, 0)
            self.assertNotIn("\u202e", output.getvalue())
            self.assertNotIn("\u2066", output.getvalue())
            self.assertIn("\\u202e\\u2066", output.getvalue())

    def test_cli_invalid_input_no_traceback_or_absolute_path(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["check", "/synthetic/nonexistent/file.epub", "--format", "json"])
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", output.getvalue())
        self.assertNotIn("/synthetic", output.getvalue())

    def test_finding_budget_reports_incompleteness(self) -> None:
        report = Report(_cap=2)
        check_text("ي" * 10, "input.txt", report)
        self.assertEqual(len(report.findings), 3)
        self.assertEqual(report.exit_code(), 2)


if __name__ == "__main__":
    unittest.main()
