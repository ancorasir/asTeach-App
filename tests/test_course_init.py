"""Fresh-workspace, preservation and hostile-input tests using disposable files."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("course_init", ROOT / "scripts/course_init.py")
init = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(init)


def refresh_manifest(root):
    """Fixture helper: model an independently rebuilt, changed source candidate."""
    path = root / init.MANIFEST
    data = json.loads(path.read_text())
    data["files"] = [init.record(name, (root / name).read_bytes()) for name in init.APP_FILES]
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


class InitializerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="asteach-init-test-")
        self.base = Path(self.temporary.name).resolve()
        self.app = self.base / "app"
        shutil.copytree(ROOT, self.app, ignore=shutil.ignore_patterns(".git"))
        self.target = self.base / "workspace"

    def tearDown(self):
        self.temporary.cleanup()

    def plan(self, target=None):
        return init.make_plan(self.app, str(target or self.target))

    def apply(self, target=None, plan_id=None):
        target = target or self.target
        if plan_id is None:
            plan_id = self.plan(target)[0]["plan_id"]
        return init.apply_plan(self.app, str(target), plan_id)

    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(self.app / "scripts/course_init.py"), *args],
                              capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})

    def test_verify_complete_positive_inventory(self):
        snapshot, manifest_hash = init.verify_app(self.app)
        self.assertEqual(set(snapshot), set(init.APP_FILES))
        self.assertEqual(len(manifest_hash), 64)

    def test_release_source_metadata_does_not_embed_its_own_commit(self):
        metadata = json.loads((self.app / init.MANIFEST).read_text())
        self.assertEqual(metadata["schema"], "asteach-app-source/v2")
        self.assertEqual(metadata["status"], "release-candidate")
        self.assertEqual(metadata["commit_binding"], "external-release-manifest")
        self.assertNotIn("app_commit", metadata)
        self.assertNotIn("source_baseline_commit", metadata)

    def test_plan_is_read_only_and_deterministic(self):
        first, payload = self.plan()
        self.assertEqual(first, self.plan()[0])
        self.assertFalse(self.target.exists())
        self.assertEqual(len(payload), 19)
        self.assertEqual(first["mapped_directory"], "course/")
        self.assertEqual(set(payload) - {"course/" + p for p in init.TEMPLATE_FILES}, {"LICENSE", "README.md", "AGENTS.md"})

    def test_apply_then_check_and_identical_no_op(self):
        plan, payload = self.plan()
        self.assertEqual(self.apply(plan_id=plan["plan_id"])["writes"], 19)
        before = {p: (self.target / p).stat().st_mtime_ns for p in payload}
        self.assertEqual(init.compare_workspace(self.target, payload)["status"], "unchanged")
        self.assertEqual(self.apply(plan_id=plan["plan_id"])["writes"], 0)
        self.assertEqual(before, {p: (self.target / p).stat().st_mtime_ns for p in payload})
        self.assertFalse((self.target / ".git").exists())
        self.assertFalse((self.target / ".course-state").exists())

    def test_wrong_or_missing_approval_never_creates(self):
        for bad in ("0" * 64, "", "PASTE_PLAN_ID_HERE", "A" * 64):
            with self.subTest(bad=bad), self.assertRaises(init.InitError):
                self.apply(plan_id=bad)
        self.assertFalse(self.target.exists())

    def test_plan_binds_destination(self):
        plan, _ = self.plan()
        with self.assertRaises(init.InitError):
            self.apply(self.base / "different", plan["plan_id"])
        self.assertFalse((self.base / "different").exists())

    def test_plan_requires_absent_even_for_empty_directory(self):
        self.target.mkdir()
        with self.assertRaises(init.InitError):
            self.plan()

    def test_existing_empty_destination_after_plan_is_not_adopted(self):
        plan, _ = self.plan()
        self.target.mkdir()
        with self.assertRaises(init.InitError):
            self.apply(plan_id=plan["plan_id"])
        self.assertEqual(list(self.target.iterdir()), [])

    def test_changed_content_is_preserved(self):
        plan, payload = self.plan()
        self.apply(plan_id=plan["plan_id"])
        path = self.target / "course/.gitbook/includes/one-page-learning-outcomes.md"
        path.write_text("Instructor-authored input\n")
        result = init.compare_workspace(self.target, payload)
        self.assertEqual(result["changed"], [path.relative_to(self.target).as_posix()])
        with self.assertRaises(init.InitError):
            self.apply(plan_id=plan["plan_id"])
        self.assertEqual(path.read_text(), "Instructor-authored input\n")

    def test_missing_and_additional_files_reported_without_reading_extra(self):
        _, payload = self.plan()
        self.apply()
        (self.target / "course/SUMMARY.md").unlink()
        extra = self.target / "course/authored.md"
        extra.write_text("Keep this input.\n")
        result = init.compare_workspace(self.target, payload)
        self.assertEqual(result["missing"], ["course/SUMMARY.md"])
        self.assertEqual(result["additional"], ["course/authored.md"])
        self.assertEqual(extra.read_text(), "Keep this input.\n")

    def test_later_git_metadata_is_reported_without_traversal(self):
        _, payload = self.plan()
        self.apply()
        metadata = self.target / ".git"
        metadata.mkdir()
        (metadata / "opaque").symlink_to(self.base / "not-present")
        result = init.compare_workspace(self.target, payload)
        self.assertEqual(result["additional"], [".git/"])

    def test_partial_failure_is_preserved_and_fresh_recovery_succeeds(self):
        plan, payload = self.plan()
        real_open = os.open
        def interrupted(path, *args, **kwargs):
            if path == "SUMMARY.md":
                raise OSError("simulated interrupted write")
            return real_open(path, *args, **kwargs)
        # Preserve the platform capability check while injecting a real write failure.
        with mock.patch.object(init.os, "open", side_effect=interrupted) as patched:
            with mock.patch.object(init.os, "supports_dir_fd", os.supports_dir_fd | {patched}):
                with self.assertRaises(init.InitError):
                    self.apply(plan_id=plan["plan_id"])
        self.assertTrue(self.target.exists())
        self.assertEqual(init.compare_workspace(self.target, payload)["status"], "drift")
        retained = {p.relative_to(self.target).as_posix(): p.read_bytes() for p in self.target.rglob("*") if p.is_file()}
        with self.assertRaises(init.InitError):
            self.apply(plan_id=plan["plan_id"])
        recovered = self.base / "recovered"
        self.apply(recovered)
        self.assertEqual(init.compare_workspace(recovered, payload)["status"], "unchanged")
        self.assertEqual(retained, {p.relative_to(self.target).as_posix(): p.read_bytes() for p in self.target.rglob("*") if p.is_file()})

    def test_recovery_from_independent_app_copy(self):
        plan, payload = self.plan()
        recovered_app = self.base / "recovered-app"
        shutil.copytree(self.app, recovered_app)
        result = init.apply_plan(recovered_app, str(self.target), plan["plan_id"])
        self.assertEqual(result["status"], "created")
        self.assertEqual(init.compare_workspace(self.target, payload)["status"], "unchanged")

    def test_parent_replacement_invalidates_plan(self):
        parent = self.base / "parent"
        parent.mkdir()
        target = parent / "workspace"
        plan, _ = self.plan(target)
        parent.rename(self.base / "retained-parent")
        parent.mkdir()
        with self.assertRaises(init.InitError):
            self.apply(target, plan["plan_id"])
        self.assertFalse(target.exists())

    def test_missing_parent_refused(self):
        with self.assertRaises(init.InitError):
            self.plan(self.base / "missing" / "workspace")

    def test_source_overlap_refused(self):
        for path in (self.app, self.app / "new-course", self.base):
            with self.subTest(path=path), self.assertRaises(init.InitError):
                self.plan(path)

    def test_symlink_parent_and_destination_refused(self):
        alias = self.base / "alias"
        alias.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(init.InitError):
            self.plan(alias / "workspace")
        self.target.symlink_to(self.base / "absent", target_is_directory=True)
        with self.assertRaises(init.InitError):
            self.plan()

    def test_symlink_course_content_refused_and_untouched(self):
        plan, payload = self.plan()
        self.apply(plan_id=plan["plan_id"])
        path = self.target / "course/README.md"
        path.unlink()
        outside = self.base / "outside.txt"
        outside.write_text("retain\n")
        path.symlink_to(outside)
        with self.assertRaises(init.InitError):
            init.compare_workspace(self.target, payload)
        with self.assertRaises(init.InitError):
            self.apply(plan_id=plan["plan_id"])
        self.assertEqual(outside.read_text(), "retain\n")

    def test_source_checksum_drift_refused(self):
        plan, _ = self.plan()
        (self.app / "templates/one-page/README.md").write_text("Changed source\n")
        with self.assertRaises(init.InitError):
            self.apply(plan_id=plan["plan_id"])
        self.assertFalse(self.target.exists())

    def test_rebuilt_changed_source_still_invalidates_plan(self):
        plan, _ = self.plan()
        (self.app / "course-template/README.md").write_text("Changed source instructions\n")
        refresh_manifest(self.app)
        with self.assertRaises(init.InitError):
            self.apply(plan_id=plan["plan_id"])
        self.assertFalse(self.target.exists())

    def test_unknown_source_file_and_directory_refused(self):
        (self.app / "unapproved.txt").write_text("extra")
        with self.assertRaises(init.InitError):
            init.verify_app(self.app)
        (self.app / "unapproved.txt").unlink()
        (self.app / "unknown-empty-directory").mkdir()
        with self.assertRaises(init.InitError):
            init.verify_app(self.app)

    def test_source_checkout_git_metadata_is_opaque_and_not_copied(self):
        metadata = self.app / ".git"
        metadata.mkdir()
        (metadata / "opaque").symlink_to(self.base / "not-present")
        snapshot, _ = init.verify_app(self.app)
        self.assertNotIn(".git", snapshot)
        self.apply()
        self.assertFalse((self.target / ".git").exists())
        (metadata / "opaque").unlink()
        metadata.rmdir()
        metadata.write_text("gitdir: deliberately-unread-fixture\n")
        self.assertNotIn(".git", init.verify_app(self.app)[0])
        (self.app / "docs/.git").mkdir()
        with self.assertRaises(init.InitError):
            init.verify_app(self.app)

    def test_source_file_or_directory_symlink_refused(self):
        path = self.app / "README.md"
        path.unlink()
        path.symlink_to(ROOT / "README.md")
        with self.assertRaises(init.InitError):
            init.verify_app(self.app)
        path.unlink()
        path.write_bytes((ROOT / "README.md").read_bytes())
        (self.app / "linked").symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(init.InitError):
            init.verify_app(self.app)

    def test_manifest_traversal_and_duplicates_refused(self):
        path = self.app / init.MANIFEST
        original = path.read_bytes()
        for name in ("../outside", "/absolute", "a/../b", "a//b", "a\\b", "C:drive", "a/./b"):
            data = json.loads(original)
            data["files"][0]["path"] = name
            path.write_text(json.dumps(data))
            with self.subTest(name=name), self.assertRaises(init.InitError):
                init.verify_app(self.app)
        path.write_bytes(b'{"schema":1,"schema":2}')
        with self.assertRaises(init.InitError):
            init.verify_app(self.app)

    def test_manifest_cannot_add_files_or_fake_a_release_pin(self):
        path = self.app / init.MANIFEST
        original = path.read_bytes()
        for mutate in (lambda value: value.update(app_commit="a" * 40),
                       lambda value: value.update(app_commit=None),
                       lambda value: value.update(source_baseline_commit="a" * 40),
                       lambda value: value.update(commit_binding="embedded"),
                       lambda value: value["files"].append(value["files"][0]),
                       lambda value: value.update(status="released"),
                       lambda value: value.update(unknown=True)):
            data = json.loads(original)
            mutate(data)
            path.write_text(json.dumps(data))
            with self.assertRaises(init.InitError):
                init.verify_app(self.app)

    def test_cli_verify_plan_apply_check_and_drift_exit_codes(self):
        self.assertEqual(self.cli("verify").returncode, 0)
        result = self.cli("plan", "--destination", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(self.cli("apply", "--destination", str(self.target), "--plan-id", plan["plan_id"]).returncode, 0)
        self.assertEqual(self.cli("check", "--destination", str(self.target)).returncode, 0)
        (self.target / "course/README.md").write_text("Authored input")
        self.assertEqual(self.cli("check", "--destination", str(self.target)).returncode, 1)
        self.assertEqual(self.cli("apply", "--destination", str(self.target), "--plan-id", plan["plan_id"]).returncode, 2)

    def test_cli_rejects_unsupported_commands(self):
        for command in ("update", "release", "adopt", "build", "repair"):
            with self.subTest(command=command):
                self.assertEqual(self.cli(command).returncode, 2)


if __name__ == "__main__":
    unittest.main()
