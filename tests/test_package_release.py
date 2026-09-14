"""Exact-source packaging and hostile bundle tests; only disposable Git fixtures."""

import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_package", ROOT / "scripts/package_release.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def fixture_git(root, *args):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_AUTHOR_NAME="Synthetic Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                       GIT_COMMITTER_NAME="Synthetic Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid",
                       GIT_AUTHOR_DATE="2000-01-01T00:00:00+00:00", GIT_COMMITTER_DATE="2000-01-01T00:00:00+00:00",
                       GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.check_output(["git", "-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgsign=false",
                                    "-C", str(root), *args], env=environment, stderr=subprocess.DEVNULL)


def fixture_commit(root):
    fixture_git(root, "add", "--all")
    fixture_git(root, "commit", "--quiet", "-m", "Synthetic release fixture")
    return fixture_git(root, "rev-parse", "HEAD").decode().strip()


class PackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory(prefix="asteach-release-fixtures-")
        cls.fixture_root = Path(cls.fixtures.name).resolve()
        cls.fixture_app = cls.fixture_root / "app"
        cls.fixture_docs = cls.fixture_root / "docs"
        shutil.copytree(ROOT, cls.fixture_app, ignore=shutil.ignore_patterns(".git"))
        # A second disposable repository is an adversarial Git-redirection target,
        # never a release input or a developer source dependency.
        shutil.copytree(ROOT, cls.fixture_docs, ignore=shutil.ignore_patterns(".git"))
        for root in (cls.fixture_app, cls.fixture_docs):
            fixture_git(root, "init", "--quiet")
        cls.app_commit = fixture_commit(cls.fixture_app)
        cls.docs_commit = fixture_commit(cls.fixture_docs)
        cls.payloads = {"app": release.read_source(cls.fixture_app, "app")}
        cls.sources = {kind: release.pinned_source(root, commit, kind)[1]
                       for kind, root, commit in (("app", cls.fixture_app, cls.app_commit),)}
        cls.bundle_bytes = release.assemble(cls.payloads, cls.sources)

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="asteach-release-test-")
        self.base = Path(self.temporary.name).resolve()
        self.app = self.base / "app source"
        self.docs = self.base / "docs source"
        shutil.copytree(self.fixture_app, self.app)
        shutil.copytree(self.fixture_docs, self.docs)

    def tearDown(self):
        self.temporary.cleanup()

    def build(self, **changes):
        args = dict(app_root=self.app, app_commit=self.app_commit,
                    output_parent=self.base, output_name="bundle")
        args.update(changes)
        return release.build(**args)

    def write_bundle(self, payload=None, name="portable"):
        bundle = self.base / name
        bundle.mkdir()
        for path, data in (payload or self.bundle_bytes).items():
            (bundle / path).write_bytes(data)
        return bundle

    def change_manifest(self, kind, mutate):
        root = self.app if kind == "app" else self.docs
        path = root / release.COMPONENTS[kind][2]
        metadata = json.loads(path.read_bytes())
        mutate(metadata)
        path.write_bytes(release.json_bytes(metadata))
        return fixture_commit(root)

    def test_real_git_tree_hash_and_exact_source_export(self):
        for kind, root, commit in (("app", self.app, self.app_commit),):
            payload, source = release.pinned_source(root, commit, kind)
            self.assertEqual(source["commit"], commit)
            self.assertEqual(source["tree"], fixture_git(root, "rev-parse", "HEAD^{tree}").decode().strip())
            self.assertEqual(set(payload), set(release.COMPONENTS[kind][3]) | {release.COMPONENTS[kind][2]})
            self.assertFalse(any(".git" in Path(name).parts for name in payload))

    def test_build_deterministic_four_files_and_native_pending(self):
        first = self.build()
        second = self.build(output_name="second")
        one, two = Path(first["destination"]), Path(second["destination"])
        self.assertEqual(sorted(p.name for p in one.iterdir()), list(release.BUNDLE_FILES))
        self.assertEqual(len(release.BUNDLE_FILES), 4)
        self.assertEqual(set(release.ARCHIVES), {"app"})
        for name in release.BUNDLE_FILES:
            self.assertEqual((one / name).read_bytes(), (two / name).read_bytes())
        checked = release.verify_bundle(one)
        self.assertEqual(checked["initializer"], "verified")
        self.assertEqual(checked["native_acceptance"], "pending")
        self.assertEqual(checked["publication"], "pending")

    def test_portable_verification_uses_no_git_or_maintainer_state(self):
        bundle = self.write_bundle()
        with mock.patch.object(release, "git", side_effect=AssertionError("must not use Git")):
            with mock.patch.dict(os.environ, {"PATH": "/nonexistent", "PYTHONPATH": "/nonexistent"}):
                self.assertEqual(release.verify_bundle(bundle)["status"], "verified")
        self.assertEqual(sorted(p.name for p in bundle.iterdir()), list(release.BUNDLE_FILES))

    def official_args(self):
        fixture_git(self.app, "tag", "v0.1", self.app_commit)
        return dict(release_mode="official", release_tag="v0.1",
                    accepted_template_sha256=release.template_digest(self.payloads["app"]),
                    authorize_publication=True)

    def test_official_build_exact_tag_digest_and_portable_verification(self):
        args = self.official_args()
        built = self.build(**args)
        again = self.build(output_name="official-again", **args)
        one, two = Path(built["destination"]), Path(again["destination"])
        for name in release.BUNDLE_FILES:
            self.assertEqual((one / name).read_bytes(), (two / name).read_bytes())
        with mock.patch.object(release, "git", side_effect=AssertionError("offline verification")):
            checked = release.verify_bundle(one)
        self.assertEqual(checked["publication"], "authorized")
        self.assertEqual(checked["native_acceptance"]["status"], "maintainer-attested")
        manifest = json.loads((one / "RELEASE-MANIFEST.json").read_bytes())
        self.assertEqual(manifest["schema"], "asteach-release/v3")
        self.assertEqual(manifest["release"]["tag"], "v0.1")
        self.assertEqual(manifest["release"]["repository"], release.OFFICIAL_REPOSITORY)
        self.assertEqual(manifest["sources"]["app"]["commit"], self.app_commit)

    def test_official_requires_all_explicit_gate_values(self):
        args = self.official_args()
        for changes in ({"authorize_publication": False}, {"release_tag": None},
                        {"release_tag": "v0.2"}, {"accepted_template_sha256": None},
                        {"accepted_template_sha256": "0" * 64}, {"release_mode": "unknown"}):
            with self.subTest(changes=changes), self.assertRaises(release.ReleaseError):
                self.build(**dict(args, **changes))
            self.assertFalse((self.base / "bundle").exists())

    def test_candidate_cannot_claim_official_gate_values(self):
        for changes in ({"release_tag": "v0.1"}, {"authorize_publication": True},
                        {"accepted_template_sha256": "0" * 64}):
            with self.subTest(changes=changes), self.assertRaises(release.ReleaseError):
                self.build(**changes)

    def test_official_missing_and_noncommit_tag_refused(self):
        args = self.official_args()
        fixture_git(self.app, "tag", "-d", "v0.1")
        with self.assertRaises(release.ReleaseError):
            self.build(**args)
        fixture_git(self.app, "tag", "v0.1", self.app_commit + "^{tree}")
        with self.assertRaises(release.ReleaseError):
            self.build(**args)
        self.assertFalse((self.base / "bundle").exists())

    def test_official_tag_change_during_assembly_refused_before_writes(self):
        args = self.official_args()
        def changed_tag(_exported):
            fixture_git(self.app, "tag", "-d", "v0.1")
        with mock.patch.object(release, "smoke_initializer", side_effect=changed_tag):
            with self.assertRaises(release.ReleaseError):
                self.build(**args)
        self.assertFalse((self.base / "bundle").exists())

    def test_official_forged_acceptance_repository_and_publication_refused(self):
        good = release.assemble(self.payloads, self.sources, True,
                                release.template_digest(self.payloads["app"]))
        for field, value in (("publication", "published"),
                             ("native_acceptance", {"status": "passed"}),
                             ("release", {"repository": "https://example.invalid", "tag": "v0.1"}),
                             ("schema", "asteach-release/v99")):
            payload = dict(good)
            manifest = json.loads(payload["RELEASE-MANIFEST.json"])
            manifest[field] = value
            payload["RELEASE-MANIFEST.json"] = release.json_bytes(manifest)
            payload["SHA256SUMS.txt"] = release.checksums({k: v for k, v in payload.items() if k != "SHA256SUMS.txt"})
            with self.subTest(field=field), self.assertRaises(release.ReleaseError):
                release.verify_bundle_bytes(payload)

    def candidate_source_payload(self):
        payload = dict(self.payloads["app"])
        prefix = release.init.USER_ROOT + "/"
        payload[prefix + "VERSION.json"] = release.json_bytes(release.init.user_version("release-candidate"))
        media = json.loads(payload[prefix + "assets/manifest.json"])
        media["status"] = "release-candidate"
        payload[prefix + "assets/manifest.json"] = release.json_bytes(media)
        guide = release.init.user_metadata("release-candidate")
        guide["files"] = [dict(release.init.record(p, payload[prefix + p]), mode="0644") for p in release.init.USER_FILES]
        payload[prefix + release.init.USER_MANIFEST] = release.json_bytes(guide)
        app = release.init.app_metadata("release-candidate")
        app["files"] = [release.init.record(p, payload[p]) for p in release.init.APP_FILES]
        payload[release.init.MANIFEST] = release.json_bytes(app)
        return payload

    def test_old_coupled_candidate_profile_remains_verifiable(self):
        app = self.candidate_source_payload()
        source = dict(self.sources["app"], tree=release.tree_hash(app),
                      source_manifest_sha256=release.verify_source_bytes("app", app))
        bundle = release.assemble({"app": app}, {"app": source})
        self.assertEqual(release.verify_bundle(self.write_bundle(bundle))["native_acceptance"], "pending")
        official = release.assemble({"app": app}, {"app": source}, True, release.template_digest(app))
        with self.assertRaisesRegex(release.ReleaseError, "release-source"):
            release.verify_bundle_bytes(official)

    def test_mixed_source_profiles_refused_even_with_correct_hashes(self):
        app = self.candidate_source_payload()
        manifest = release.init.app_metadata("release-source")
        manifest["files"] = [release.init.record(p, app[p]) for p in release.init.APP_FILES]
        app[release.init.MANIFEST] = release.json_bytes(manifest)
        with self.assertRaisesRegex(release.ReleaseError, "user guide"):
            release.verify_source_bytes("app", app)

    def test_exact_full_lowercase_commit_required(self):
        for commit in ("HEAD", "main", self.app_commit[:12], "A" * 40, "z" * 40, None):
            with self.subTest(commit=commit), self.assertRaises(release.ReleaseError):
                self.build(app_commit=commit)
        self.assertFalse((self.base / "bundle").exists())

    def test_stale_valid_commit_refused(self):
        (self.app / "README.md").write_bytes((self.app / "README.md").read_bytes() + b"\n")
        release.refresh_app_manifest(self.app)
        new_commit = fixture_commit(self.app)
        self.assertNotEqual(new_commit, self.app_commit)
        with self.assertRaisesRegex(release.ReleaseError, "stale"):
            self.build()

    def test_modified_staged_untracked_and_ignored_sources_refused(self):
        path = self.app / "README.md"
        path.write_bytes(path.read_bytes() + b"changed")
        with self.assertRaises(release.ReleaseError):
            self.build()
        fixture_git(self.app, "add", "README.md")
        with self.assertRaises(release.ReleaseError):
            self.build()
        path.write_bytes(self.payloads["app"]["README.md"])
        fixture_git(self.app, "add", "README.md")
        for name in ("unknown.txt", ".DS_Store"):
            extra = self.app / name
            extra.write_text("Synthetic unknown")
            with self.subTest(name=name), self.assertRaises(release.ReleaseError):
                self.build()
            extra.unlink()

    def test_assume_unchanged_cannot_hide_source_drift(self):
        fixture_git(self.app, "update-index", "--assume-unchanged", "README.md", release.init.MANIFEST)
        (self.app / "README.md").write_bytes(b"Changed but hidden from status\n")
        release.refresh_app_manifest(self.app)
        self.assertEqual(fixture_git(self.app, "status", "--porcelain"), b"")
        with self.assertRaisesRegex(release.ReleaseError, "committed tree differs"):
            self.build()

    def test_unknown_committed_files_even_manifest_listed_refused(self):
        (self.app / "private-notes.txt").write_text("Synthetic forbidden fixture")
        commit = self.change_manifest("app", lambda m: m["files"].append(release.init.record("private-notes.txt", b"Synthetic forbidden fixture")))
        with self.assertRaises(release.ReleaseError):
            self.build(app_commit=commit)

    def test_missing_source_and_unknown_empty_directory_refused(self):
        missing = self.app / "README.md"
        missing.unlink()
        with self.assertRaises(release.ReleaseError):
            self.build()
        missing.write_bytes(self.payloads["app"]["README.md"])
        (self.app / "unknown-empty").mkdir()
        with self.assertRaises(release.ReleaseError):
            self.build()

    def test_nested_and_nonroot_sources_refused(self):
        for root in (self.app / "docs", self.app / "docs/user", self.base):
            with self.subTest(root=root), self.assertRaises(release.ReleaseError):
                self.build(app_root=root)

    def test_worktree_metadata_file_and_alternate_objects_refused(self):
        metadata = self.app / ".git"
        metadata.rename(self.base / "retained-metadata")
        metadata.write_text("gitdir: ../retained-metadata\n")
        with self.assertRaises(release.ReleaseError):
            self.build()
        metadata.unlink()
        (self.base / "retained-metadata").rename(metadata)
        (metadata / "objects/info/alternates").write_text("/synthetic/unavailable\n")
        with self.assertRaises(release.ReleaseError):
            self.build()

    def test_internal_git_object_store_symlink_refused_before_git(self):
        objects = self.app / ".git/objects"
        preserved = self.base / "preserved-app-objects"
        objects.rename(preserved)
        objects.symlink_to(preserved, target_is_directory=True)
        with mock.patch.object(release, "git", side_effect=AssertionError("must reject before Git")):
            with self.assertRaises(release.ReleaseError):
                self.build()
        self.assertFalse((self.base / "bundle").exists())

    def test_git_metadata_file_symlink_refused_before_git(self):
        config = self.app / ".git/config"
        preserved = self.base / "preserved-config"
        config.rename(preserved)
        config.symlink_to(preserved)
        with mock.patch.object(release, "git", side_effect=AssertionError("must reject before Git")):
            with self.assertRaises(release.ReleaseError):
                self.build()

    def test_same_size_dirty_file_does_not_execute_local_clean_filter(self):
        marker = self.base / "filter-executed"
        fixture_git(self.app, "config", "filter.probe.clean", "tee " + str(marker))
        (self.app / ".git/info/attributes").write_text("README.md filter=probe\n")
        readme = self.app / "README.md"
        original = readme.read_bytes()
        readme.write_bytes(b"!" + original[1:])
        with self.assertRaises(release.ReleaseError):
            self.build()
        self.assertFalse(marker.exists())
        # Even with a refreshed source manifest, committed bytes differ and no
        # content-conversion command is invoked during index comparison.
        release.refresh_app_manifest(self.app)
        with self.assertRaises(release.ReleaseError):
            self.build()
        self.assertFalse(marker.exists())

    def test_staged_content_with_restored_worktree_refused(self):
        readme = self.app / "README.md"
        original = readme.read_bytes()
        readme.write_bytes(b"Synthetic staged edit\n")
        fixture_git(self.app, "add", "README.md")
        readme.write_bytes(original)
        with self.assertRaisesRegex(release.ReleaseError, "index is dirty"):
            self.build()

    def test_unstaged_mode_drift_in_source_guide_and_manifests_refused(self):
        for root, kind in ((self.app, "app"),):
            for filemode in ("true", "false"):
                fixture_git(root, "config", "core.filemode", filemode)
                for name in ("README.md", release.init.MANIFEST, "docs/user/README.md", "docs/user/DOCS-MANIFEST.json"):
                    path = root / name
                    original = path.read_bytes()
                    os.chmod(path, 0o755)
                    with self.subTest(kind=kind, name=name, filemode=filemode):
                        with self.assertRaisesRegex(release.ReleaseError, "source file mode must be 0644"):
                            self.build()
                        self.assertEqual(path.read_bytes(), original)
                        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o755)
                        self.assertFalse((self.base / "bundle").exists())
                    os.chmod(path, 0o644)

    def test_promisor_configuration_and_store_refused(self):
        fixture_git(self.app, "config", "remote.fixture.promisor", "true")
        with self.assertRaisesRegex(release.ReleaseError, "promisor"):
            self.build()
        fixture_git(self.app, "config", "--unset", "remote.fixture.promisor")
        pack = self.app / ".git/objects/pack"
        pack.mkdir(exist_ok=True)
        (pack / "synthetic.promisor").write_bytes(b"")
        with self.assertRaisesRegex(release.ReleaseError, "promisor"):
            self.build()

    def test_tracked_symlink_refused(self):
        path = self.app / "README.md"
        path.unlink()
        path.symlink_to(self.fixture_app / "README.md")
        commit = fixture_commit(self.app)
        with self.assertRaises(release.ReleaseError):
            self.build(app_commit=commit)

    def test_submodule_and_executable_modes_refused(self):
        fixture_git(self.app, "update-index", "--add", "--cacheinfo", "160000," + self.docs_commit + ",synthetic-submodule")
        fixture_git(self.app, "commit", "--quiet", "-m", "Synthetic submodule fixture")
        commit = fixture_git(self.app, "rev-parse", "HEAD").decode().strip()
        with self.assertRaises(release.ReleaseError):
            self.build(app_commit=commit)
        os.chmod(self.docs / "README.md", 0o755)
        commit = fixture_commit(self.docs)
        with self.assertRaises(release.ReleaseError):
            release.pinned_source(self.docs, commit, "app")

    def test_source_manifest_version_commit_and_acceptance_mutations_refused(self):
        mutations = (("app", "status", "released"), ("app", "app_commit", "a" * 40),
                     ("app", "docs_version", "v0.2"), ("app", "schema", True),
                     ("app", "license_overrides", {}), ("app", "docs_commit", None))
        for kind, key, value in mutations:
            payload = dict(self.payloads[kind])
            name = release.COMPONENTS[kind][2]
            metadata = json.loads(payload[name])
            metadata[key] = value
            payload[name] = release.json_bytes(metadata)
            with self.subTest(kind=kind, key=key), self.assertRaises(release.ReleaseError):
                release.verify_source_bytes(kind, payload)

    def test_docs_version_mismatch_even_with_refreshed_inventory_refused(self):
        payload = dict(self.payloads["app"])
        version = json.loads(payload["docs/user/VERSION.json"])
        version["native_acceptance"] = "accepted"
        payload["docs/user/VERSION.json"] = release.json_bytes(version)
        metadata = release.init.user_metadata()
        metadata["files"] = [dict(release.init.record(name, payload["docs/user/" + name]), mode="0644")
                             for name in release.init.USER_FILES]
        payload["docs/user/DOCS-MANIFEST.json"] = release.json_bytes(metadata)
        metadata = release.app_metadata()
        metadata["files"] = [release.init.record(name, payload[name]) for name in release.init.APP_FILES]
        payload[release.init.MANIFEST] = release.json_bytes(metadata)
        with self.assertRaises(release.ReleaseError):
            release.verify_source_bytes("app", payload)

    def test_output_collision_and_out_of_scope_names_refused(self):
        target = self.base / "bundle"
        target.mkdir()
        marker = target / "authored.txt"
        marker.write_text("preserve")
        with self.assertRaises(release.ReleaseError):
            self.build()
        self.assertEqual(marker.read_text(), "preserve")
        for name in ("../escape", "/absolute", ".", "..", "with/slash", "a\\b", "", "a\nname"):
            with self.subTest(name=name), self.assertRaises(release.ReleaseError):
                self.build(output_name=name)
        with self.assertRaises(release.ReleaseError):
            self.build(output_parent=self.app, output_name="nested")
        with self.assertRaises(release.ReleaseError):
            self.build(output_parent=self.base / "missing")

    def test_symlink_source_parent_output_and_bundle_refused(self):
        alias = self.base / "alias"
        alias.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(release.ReleaseError):
            self.build(app_root=alias / self.app.name)
        with self.assertRaises(release.ReleaseError):
            self.build(output_parent=alias)
        bundle = self.write_bundle()
        path = bundle / "START-HERE.md"
        original = path.read_bytes()
        path.unlink()
        outside = self.base / "outside"
        outside.write_bytes(original)
        path.symlink_to(outside)
        with self.assertRaises(release.ReleaseError):
            release.verify_bundle(bundle)
        self.assertEqual(outside.read_bytes(), original)

    def test_build_rechecks_source_before_writing(self):
        real = release.smoke_initializer
        def changed(exported):
            real(exported)
            (self.app / "README.md").write_text("New concurrent edit")
        with mock.patch.object(release, "smoke_initializer", side_effect=changed):
            with self.assertRaises(release.ReleaseError):
                self.build()
        self.assertFalse((self.base / "bundle").exists())

    def test_archive_duplicates_traversal_symlinks_and_extra_files_refused(self):
        for member, mode in (("asTeach-App/../escape", stat.S_IFREG | 0o644),
                             ("asTeach-App/README.md", stat.S_IFLNK | 0o777),
                             ("asTeach-App/private.txt", stat.S_IFREG | 0o644)):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as archive:
                for index, (name, data) in enumerate(sorted(self.payloads["app"].items())):
                    info = zipfile.ZipInfo(member if index == 0 else "asTeach-App/" + name, release.ZIP_DATE)
                    info.create_system = 3
                    info.external_attr = mode << 16 if index == 0 else (stat.S_IFREG | 0o644) << 16
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)  # Deliberate duplicate-member fixture.
                        archive.writestr(info, data)
            with self.subTest(member=member), self.assertRaises(release.ReleaseError):
                release.read_archive("app", stream.getvalue())

    def test_archive_noncanonical_bytes_and_tampering_refused(self):
        original = self.bundle_bytes[release.ARCHIVES["app"]]
        for data in (original + b"hidden bytes", b"not a zip", original[:-20]):
            with self.subTest(length=len(data)), self.assertRaises((release.ReleaseError, zipfile.BadZipFile)):
                release.read_archive("app", data)

    def test_bundle_checksum_unknown_files_and_directories_refused(self):
        bundle = self.write_bundle()
        (bundle / "START-HERE.md").write_text("Altered instructions")
        with self.assertRaises(release.ReleaseError):
            release.verify_bundle(bundle)
        (bundle / "START-HERE.md").write_bytes(self.bundle_bytes["START-HERE.md"])
        extra = bundle / "private-record.txt"
        extra.write_text("Synthetic extra")
        with self.assertRaises(release.ReleaseError):
            release.verify_bundle(bundle)
        extra.unlink()
        (bundle / "extra").mkdir()
        with self.assertRaises(release.ReleaseError):
            release.verify_bundle(bundle)

    def test_release_cannot_assert_acceptance_or_fake_tree(self):
        for field, value in (("native_acceptance", "accepted"), ("publication", "published"),
                             ("status", "public-release"), ("tree", "a" * 40), ("commit", "HEAD")):
            payload = dict(self.bundle_bytes)
            metadata = json.loads(payload["RELEASE-MANIFEST.json"])
            if field in ("tree", "commit"):
                metadata["sources"]["app"][field] = value
            else:
                metadata[field] = value
            payload["RELEASE-MANIFEST.json"] = release.json_bytes(metadata)
            payload["SHA256SUMS.txt"] = release.checksums({name: data for name, data in payload.items() if name != "SHA256SUMS.txt"})
            with self.subTest(field=field), self.assertRaises(release.ReleaseError):
                release.verify_bundle_bytes(payload)

    def test_duplicate_json_and_false_size_manifest_records_refused(self):
        payload = dict(self.payloads["app"])
        payload[release.init.MANIFEST] = b'{"schema":1,"schema":2}'
        with self.assertRaises(release.ReleaseError):
            release.verify_source_bytes("app", payload)
        for name in ("../escape", "a//b", "a\\b", "/absolute", "C:drive"):
            metadata = json.loads(self.payloads["app"][release.init.MANIFEST])
            metadata["files"][0]["path"] = name
            payload[release.init.MANIFEST] = release.json_bytes(metadata)
            with self.subTest(name=name), self.assertRaises(release.ReleaseError):
                release.verify_source_bytes("app", payload)
        metadata = json.loads(self.payloads["app"][release.init.MANIFEST])
        metadata["files"][0]["size"] = True
        payload[release.init.MANIFEST] = release.json_bytes(metadata)
        with self.assertRaises(release.ReleaseError):
            release.verify_source_bytes("app", payload)

    def test_git_environment_redirection_is_ignored(self):
        with mock.patch.dict(os.environ, {"GIT_DIR": str(self.docs / ".git"), "GIT_WORK_TREE": str(self.docs)}):
            payload, source = release.pinned_source(self.app, self.app_commit, "app")
        self.assertEqual(source["commit"], self.app_commit)
        self.assertEqual(payload, self.payloads["app"])

    def test_cli_verify_build_and_error_exit_codes(self):
        bundle = self.write_bundle()
        command = [sys.executable, "-B", str(ROOT / "scripts/package_release.py")]
        result = subprocess.run(command + ["verify", "--bundle", str(bundle)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(command + ["build", "--app-root", str(self.app), "--app-commit", self.app_commit,
                                          "--output-parent", str(self.base), "--output-name", "cli-bundle"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(command + ["build", "--app-root", str(self.app), "--app-commit", self.app_commit,
                                          "--docs-root", str(self.docs), "--docs-commit", self.docs_commit,
                                          "--output-parent", str(self.base), "--output-name", "legacy"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Two-root builds are legacy v1", result.stderr)
        self.assertFalse((self.base / "legacy").exists())
        result = subprocess.run(command + ["verify", "--bundle", str(self.base / "missing")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        for mode in ("publish", "release", "accept", "tag"):
            self.assertEqual(subprocess.run(command + [mode], capture_output=True).returncode, 2)

    def test_legacy_bundle_is_identified_before_inventory_failure(self):
        payload = {"RELEASE-MANIFEST.json": b'{"schema":"asteach-release/v1"}',
                   "asTeach-Docs-v0.1.1.zip": b"untrusted legacy placeholder"}
        with self.assertRaisesRegex(release.ReleaseError, "trusted.*original App ZIP"):
            release.verify_bundle_bytes(payload)
        bundle = self.write_bundle(payload, name="legacy")
        with self.assertRaisesRegex(release.ReleaseError, "trusted.*original App ZIP"):
            release.verify_bundle(bundle)

    def test_packaging_has_no_dependency_on_private_development_repository(self):
        shutil.rmtree(self.docs)
        self.assertEqual(self.build()["status"], "created")

    def test_user_manifest_refresh_rejects_unknown_and_version_drift(self):
        path = self.app / "docs/user/private-note.md"
        path.write_text("Synthetic unapproved candidate")
        with self.assertRaisesRegex(release.ReleaseError, "unknown user guide"):
            release.refresh_user_manifest(self.app)
        path.unlink()
        path = self.app / "docs/user/VERSION.json"
        value = json.loads(path.read_bytes())
        value["docs_version"] = "v0.2"
        path.write_bytes(release.json_bytes(value))
        with self.assertRaisesRegex(release.ReleaseError, "version metadata mismatch"):
            release.refresh_user_manifest(self.app)


if __name__ == "__main__":
    unittest.main()
