"""Integrated guide boundaries, content integrity and accessible media checks."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("guide_checks", ROOT / "scripts/check_docs.py")
guide = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guide)


class GuideTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="asteach-guide-test-")
        self.app = Path(self.temporary.name).resolve() / "App"
        shutil.copytree(ROOT, self.app, ignore=shutil.ignore_patterns(".git"))
        self.root = self.app / "docs/user"

    def tearDown(self):
        self.temporary.cleanup()

    def refresh(self):
        metadata = guide.init.user_metadata()
        metadata["files"] = [dict(guide.init.record(name, (self.root / name).read_bytes()), mode="0644")
                             for name in guide.init.USER_FILES]
        (self.root / guide.MANIFEST).write_text(json.dumps(metadata))

    def check(self):
        with mock.patch.object(guide, "ROOT", self.root), mock.patch.object(guide, "APP_ROOT", self.app):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                guide.check()
                return json.loads(output.getvalue())

    def test_integrated_guide_pages_figures_and_version(self):
        result = self.check()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["guide_pages"], 10)
        self.assertEqual(result["schematics"], 6)
        self.assertEqual(result["native_acceptance"], "pending")
        self.assertEqual(guide.init.user_version()["docs_version"], "v0.1.1")

    def test_guide_cannot_claim_native_acceptance_or_different_version(self):
        for field, value in (("native_acceptance", "pass"), ("docs_version", "v0.2"), ("schema_version", True)):
            version = guide.init.user_version()
            version[field] = value
            (self.root / "VERSION.json").write_text(json.dumps(version))
            self.refresh()
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check()

    def test_content_hash_drift_and_unknown_empty_directory_refused(self):
        readme = self.root / "README.md"
        original = readme.read_bytes()
        readme.write_bytes(original + b"\nSynthetic unreviewed change\n")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            self.check()
        readme.write_bytes(original)
        (self.root / "private-notes").mkdir()
        with self.assertRaisesRegex(ValueError, "inventory mismatch"):
            self.check()

    def test_symlink_and_nested_git_refused(self):
        readme = self.root / "README.md"
        readme.unlink()
        readme.symlink_to(ROOT / "README.md")
        with self.assertRaises(guide.init.InitError):
            self.check()
        readme.unlink()
        shutil.copyfile(ROOT / "docs/user/README.md", readme)
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(ValueError, "inventory mismatch"):
            self.check()

    def test_parent_links_allow_only_named_public_entry_points(self):
        readme = self.root / "README.md"
        original = readme.read_text()
        for target in ("../../PROVENANCE.md", "../../../private.md", "../../templates/one-page/README.md"):
            readme.write_text(original + "\n[Invalid link](" + target + ")\n")
            self.refresh()
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "Link escapes boundary"):
                self.check()

    def test_remote_images_and_wrong_alt_text_refused_after_refresh(self):
        readme = self.root / "README.md"
        original = readme.read_text()
        for text in (original + "\n![Remote](https://example.invalid/image.svg)\n",
                     original.replace("![Schematic: one Home", "![Wrong: one Home")):
            readme.write_text(text)
            self.refresh()
            with self.assertRaises(ValueError):
                self.check()

    def test_media_cannot_change_license_or_execute_svg(self):
        manifest = self.root / "assets/manifest.json"
        media = json.loads(manifest.read_bytes())
        media["assets"][0]["license"] = "MIT"
        manifest.write_text(json.dumps(media))
        self.refresh()
        with self.assertRaisesRegex(ValueError, "diagram license"):
            self.check()
        shutil.copyfile(ROOT / "docs/user/assets/manifest.json", manifest)
        svg = self.root / "assets/01-course-overview.svg"
        svg.write_text(svg.read_text().replace("</svg>", "<script>void(0)</script></svg>"))
        self.refresh()
        with self.assertRaisesRegex(ValueError, "embedded SVG content"):
            self.check()

    def test_duplicate_metadata_fields_refused(self):
        (self.root / guide.MANIFEST).write_text('{"schema_version":3,"schema_version":3}')
        with self.assertRaisesRegex(guide.init.InitError, "duplicate JSON key"):
            self.check()


if __name__ == "__main__":
    unittest.main()
