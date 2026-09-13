#!/usr/bin/env python3
"""Build or verify an offline, exact-source asTeach release-candidate bundle."""

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import zipfile

SPEC = importlib.util.spec_from_file_location("asteach_initializer", Path(__file__).with_name("course_init.py"))
init = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(init)
ReleaseError = init.InitError
COMPONENTS = {
    "app": ("asTeach-App", "v0.1", init.MANIFEST, init.APP_FILES),
}
ARCHIVES = {key: name + "-" + version + ".zip" for key, (name, version, _, _) in COMPONENTS.items()}
ASSETS = tuple(sorted((*ARCHIVES.values(), "START-HERE.md")))
BUNDLE_FILES = tuple(sorted((*ASSETS, "RELEASE-MANIFEST.json", "SHA256SUMS.txt")))
ZIP_DATE = (1980, 1, 1, 0, 0, 0)
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
LEGACY_MESSAGE = ("Legacy asteach-release/v1 bundle: verify it with the trusted "
                  "scripts/package_release.py inside its original App ZIP; retain all five original files.")


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def parse_json(data):
    try:
        return json.loads(data, object_pairs_hook=init.reject_duplicates)
    except (ValueError, UnicodeError) as error:
        raise ReleaseError("invalid JSON: " + str(error))


def exact_fields(value, expected, context):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ReleaseError("unsupported " + context + " fields")


def check_values(value, expected, context):
    if any(type(value[key]) is not type(wanted) or value[key] != wanted for key, wanted in expected.items()):
        raise ReleaseError("unsupported " + context + " metadata")


def app_metadata():
    return init.app_metadata()


def verify_source_bytes(kind, payload):
    _, _, manifest_name, allowlist = COMPONENTS[kind]
    if set(payload) != set(allowlist) | {manifest_name}:
        raise ReleaseError(kind + " inventory does not match the complete positive allowlist")
    metadata = parse_json(payload[manifest_name])
    expected = app_metadata()
    exact_fields(metadata, (*expected, "files"), kind + " source manifest")
    check_values(metadata, expected, kind + " source manifest")
    entries = metadata["files"]
    if not isinstance(entries, list):
        raise ReleaseError(kind + " manifest inventory must be a list")
    for entry in entries:
        exact_fields(entry, ("path", "size", "sha256"), "file record")
        init.safe_relative(entry["path"])
        if type(entry["size"]) is not int or entry["size"] < 0:
            raise ReleaseError("invalid file size")
    expected_entries = [init.record(name, payload[name]) for name in allowlist]
    if entries != expected_entries:
        raise ReleaseError(kind + " source manifest inventory or checksum mismatch")
    if payload["VERSION"] != b"v0.1\n":
        raise ReleaseError("App VERSION mismatch")
    init.verify_user_source(payload)
    return init.digest(payload[manifest_name])


def read_source(root, kind):
    root = init.inspect_path(root)
    files, directories = init.tree_inventory(root, skip_git=True)
    files.discard(".git")
    directories.discard(".git")
    _, _, manifest, allowlist = COMPONENTS[kind]
    expected = set(allowlist) | {manifest}
    if files != expected or directories != init.parent_paths(expected):
        raise ReleaseError(kind + " source has missing or unknown files/directories")
    payload = {name: read_source_file(root, name) for name in sorted(expected)}
    verify_source_bytes(kind, payload)
    return payload


def read_source_file(root, name):
    path = init.inspect_path(root / name)
    if stat.S_IMODE(path.stat().st_mode) != 0o644:
        raise ReleaseError("source file mode must be 0644: " + name)
    data = init.read_regular(path)
    if stat.S_IMODE(path.stat().st_mode) != 0o644:
        raise ReleaseError("source file mode changed while reading: " + name)
    return data


def refresh_app_manifest(root):
    """Explicit developer operation; never silently repair manifests during build."""
    root = init.inspect_path(root)
    files, directories = init.tree_inventory(root, skip_git=True)
    files.discard(".git")
    directories.discard(".git")
    expected = set(init.APP_FILES) | {init.MANIFEST}
    if files != expected or directories != init.parent_paths(expected):
        raise ReleaseError("cannot refresh an incomplete or unknown App inventory")
    snapshot = {name: read_source_file(root, name) for name in init.APP_FILES}
    init.verify_user_source(snapshot)
    metadata = app_metadata()
    metadata["files"] = [init.record(name, snapshot[name]) for name in init.APP_FILES]
    path = init.inspect_path(root / init.MANIFEST)
    read_source_file(root, init.MANIFEST)
    with path.open("wb") as stream:
        stream.write(json_bytes(metadata))
    read_source(root, "app")
    return {"status": "refreshed", "manifest": str(path), "sha256": init.digest(init.read_regular(path))}


def refresh_user_manifest(root):
    """Refresh only an explicitly reviewed, complete guide inventory."""
    root = init.inspect_path(root)
    guide = init.inspect_path(root / init.USER_ROOT)
    files, directories = init.tree_inventory(guide)
    expected = set(init.USER_FILES) | {init.USER_MANIFEST}
    if files != expected or directories != init.parent_paths(expected):
        raise ReleaseError("cannot refresh an incomplete or unknown user guide inventory")
    version = parse_json(read_source_file(guide, "VERSION.json"))
    if init.canonical(version) != init.canonical(init.user_version()):
        raise ReleaseError("user guide version metadata mismatch")
    metadata = init.user_metadata()
    metadata["files"] = [dict(init.record(name, read_source_file(guide, name)), mode="0644")
                         for name in init.USER_FILES]
    path = init.inspect_path(guide / init.USER_MANIFEST)
    read_source_file(guide, init.USER_MANIFEST)
    with path.open("wb") as stream:
        stream.write(json_bytes(metadata))
    return {"status": "refreshed", "manifest": str(path), "sha256": init.digest(init.read_regular(path))}


def git(root, *args, allowed_codes=(0,)):
    # Ignore inherited repository redirection, replacement objects and executable
    # fsmonitor configuration. No filters, hooks or network commands are used.
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0",
                       GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    result = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
                             "-C", str(root), *args], capture_output=True, env=environment)
    if result.returncode not in allowed_codes:
        raise ReleaseError("Git validation failed: " + result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def full_commit(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ReleaseError("each source commit must be an exact lowercase 40-hex Git SHA-1")
    return value


def pinned_source(root, commit, kind):
    commit = full_commit(commit)
    root = init.inspect_path(root)
    metadata = init.inspect_path(root / ".git")
    if not metadata.is_dir():
        raise ReleaseError("source must own an independent .git directory")
    # Inspect types before Git can follow internal redirects. No metadata file
    # contents are read by this traversal or included in the exported source.
    metadata_files, _ = init.tree_inventory(metadata)
    if (metadata / "commondir").exists() or (metadata / "objects/info/alternates").exists():
        raise ReleaseError("shared Git metadata or alternate object stores are unsupported")
    if any(name.endswith(".promisor") for name in metadata_files):
        raise ReleaseError("partial/promisor object stores are unsupported")
    if git(root, "config", "--local", "--includes", "--name-only", "--get-regexp",
           r"^(extensions\.partialclone|remote\..*\.promisor)$", allowed_codes=(0, 1)):
        raise ReleaseError("partial/promisor source configuration is unsupported")
    if Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()) != root:
        raise ReleaseError("source path must be the exact Git working tree root")
    if Path(os.fsdecode(git(root, "rev-parse", "--absolute-git-dir")).strip()) != metadata:
        raise ReleaseError("source Git directory is redirected")
    if git(root, "rev-parse", "--show-object-format").strip() != b"sha1":
        raise ReleaseError("only 40-hex SHA-1 Git repositories are supported")
    if git(root, "rev-parse", "HEAD").decode().strip() != commit:
        raise ReleaseError(kind + " checkout is stale: HEAD does not equal the supplied commit")
    if git(root, "cat-file", "-t", commit).strip() != b"commit":
        raise ReleaseError("source pin must identify a commit object")
    current = read_source(root, kind)
    exported = {}
    committed_index = {}
    for record in git(root, "ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if not record:
            continue
        header, raw_name = record.split(b"\t", 1)
        mode, object_type, oid = header.split(b" ")
        name = init.safe_relative(raw_name.decode("utf-8"))
        if mode != b"100644" or object_type != b"blob":
            raise ReleaseError("only regular 0644 source files are allowed: " + name)
        if name not in current or name in exported:
            raise ReleaseError("unknown or duplicate committed path: " + name)
        committed_index[name] = (mode, oid, b"0")
        exported[name] = git(root, "cat-file", "blob", oid.decode("ascii"))
    # `status` and working-tree diffs can execute configured clean filters.
    # ls-files --stage reads the index without converting working-file contents.
    index = {}
    for record in git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        header, raw_name = record.split(b"\t", 1)
        mode, oid, stage = header.split(b" ")
        name = init.safe_relative(raw_name.decode("utf-8"))
        if name in index or stage != b"0":
            raise ReleaseError(kind + " source index is unmerged")
        index[name] = (mode, oid, stage)
    if index != committed_index:
        raise ReleaseError(kind + " source index is dirty")
    if exported != current:
        raise ReleaseError(kind + " committed tree differs from the verified working files")
    tree = git(root, "rev-parse", commit + "^{tree}").decode().strip()
    if tree != tree_hash(exported):
        raise ReleaseError(kind + " exported tree hash mismatch")
    return exported, {"version": COMPONENTS[kind][1], "commit": commit, "tree": tree,
                      "source_manifest_sha256": verify_source_bytes(kind, exported),
                      "archive": ARCHIVES[kind]}


def git_hash(kind, data):
    return hashlib.sha1(kind.encode() + b" " + str(len(data)).encode() + b"\0" + data).digest()


def tree_hash(payload):
    """Reproduce Git's file/tree object hashing without local Git metadata."""
    tree = {}
    for name, data in payload.items():
        current = tree
        pieces = init.safe_relative(name).split("/")
        for piece in pieces[:-1]:
            current = current.setdefault(piece, {})
        current[pieces[-1]] = data
    def encode(current):
        parts = []
        for name, data in sorted(current.items(), key=lambda item: (item[0] + ("/" if isinstance(item[1], dict) else "")).encode()):
            directory = isinstance(data, dict)
            oid = encode(data) if directory else git_hash("blob", data)
            parts.append((b"40000 " if directory else b"100644 ") + name.encode() + b"\0" + oid)
        return git_hash("tree", b"".join(parts))
    return encode(tree).hex()


def archive_bytes(kind, payload):
    stream = io.BytesIO()
    prefix = COMPONENTS[kind][0] + "/"
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(payload):
            info = zipfile.ZipInfo(prefix + name, ZIP_DATE)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, payload[name])
    return stream.getvalue()


def read_archive(kind, data):
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ReleaseError("archive exceeds the release size limit")
    _, _, manifest, allowlist = COMPONENTS[kind]
    expected = set(allowlist) | {manifest}
    payload = {}
    prefix = COMPONENTS[kind][0] + "/"
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if len(archive.infolist()) != len(expected) or archive.comment:
            raise ReleaseError("archive member count or comment mismatch")
        for info in archive.infolist():
            init.safe_relative(info.filename)
            if not info.filename.startswith(prefix):
                raise ReleaseError("archive has an unexpected root")
            name = info.filename[len(prefix):]
            if name not in expected or name in payload:
                raise ReleaseError("unknown or duplicate archive member")
            if info.external_attr != (stat.S_IFREG | 0o644) << 16 or info.create_system != 3:
                raise ReleaseError("archive contains unsafe file modes")
            if info.file_size > MAX_ARCHIVE_BYTES or info.compress_type != zipfile.ZIP_STORED:
                raise ReleaseError("unexpected compressed or oversized member")
            if info.date_time != ZIP_DATE or info.extra or info.comment or info.flag_bits & 1:
                raise ReleaseError("noncanonical archive metadata")
            payload[name] = archive.read(info)
    verify_source_bytes(kind, payload)
    if archive_bytes(kind, payload) != data:
        raise ReleaseError("archive is not the canonical deterministic byte stream")
    return payload


def start_here(sources):
    return ("# asTeach private release candidate\n\n"
            "App v0.1 includes the Docs v0.1.1 user guide in one archive. Native GitBook\n"
            "acceptance and publication remain pending. No tag or hosted release is claimed.\n\n"
            "- App source commit: `" + sources["app"]["commit"] + "`\n\n"
            "Compare SHA256SUMS.txt with a trusted publisher record before running code.\n"
            "Checksums verify integrity; they do not authenticate the publisher.\n"
            "RELEASE-MANIFEST.json records exact source pins, tree hashes and asset hashes.\n\n"
            "Extract [App v0.1](asTeach-App-v0.1.zip) and follow asTeach-App/START-HERE.md.\n"
            "The guide is asTeach-App/docs/user/README.md; technical notes are in docs/technical/.\n"
            "Keep the ZIP and these three handoff files together. The course mapping is\n"
            "the fresh workspace's course/ directory, never the App source or guide root.\n\n"
            "From the extracted App folder, verify this complete bundle with Python 3.9+:\n\n"
            "```bash\npython3 -B scripts/package_release.py verify --bundle /absolute/path/to/bundle\n```\n\n"
            "Verification uses temporary files and no Git, network or maintainer state.\n"
            "The optional course initializer needs Python; manual copying remains supported.\n"
            "Repository/Space creation, mappings, access and publication are separate\n"
            "user-controlled steps. Original App code/template is MIT; docs/user/ and its adapted checker\n"
            "are CC BY 4.0. Instructor and student\n"
            "content remains outside these product ownership claims.\n").encode()


def checksums(payload):
    return "".join(init.digest(payload[name]) + "  " + name + "\n" for name in sorted(payload)).encode()


def assemble(payloads, sources):
    payload = {ARCHIVES[kind]: archive_bytes(kind, payloads[kind]) for kind in COMPONENTS}
    payload["START-HERE.md"] = start_here(sources)
    manifest = {"schema": "asteach-release/v2", "status": "private-release-candidate",
                "app_version": init.VERSION, "docs_version": init.DOCS_VERSION,
                "native_acceptance": "pending", "publication": "pending", "sources": sources,
                "assets": [init.record(name, payload[name]) for name in ASSETS],
                "self_excluded": ["RELEASE-MANIFEST.json", "SHA256SUMS.txt"]}
    payload["RELEASE-MANIFEST.json"] = json_bytes(manifest)
    payload["SHA256SUMS.txt"] = checksums(payload)
    return payload


def verify_bundle_bytes(payload):
    if "RELEASE-MANIFEST.json" in payload:
        legacy = parse_json(payload["RELEASE-MANIFEST.json"])
        if isinstance(legacy, dict) and legacy.get("schema") == "asteach-release/v1":
            raise ReleaseError(LEGACY_MESSAGE)
    if set(payload) != set(BUNDLE_FILES):
        raise ReleaseError("bundle must contain exactly the four release files")
    manifest = parse_json(payload["RELEASE-MANIFEST.json"])
    fixed = {"schema": "asteach-release/v2", "status": "private-release-candidate",
             "app_version": init.VERSION, "docs_version": init.DOCS_VERSION,
             "native_acceptance": "pending", "publication": "pending",
             "self_excluded": ["RELEASE-MANIFEST.json", "SHA256SUMS.txt"]}
    exact_fields(manifest, (*fixed, "sources", "assets"), "release manifest")
    check_values(manifest, fixed, "release manifest")
    exact_fields(manifest["sources"], COMPONENTS, "source pins")
    if manifest["assets"] != [init.record(name, payload[name]) for name in ASSETS]:
        raise ReleaseError("release asset hashes differ")
    if payload["SHA256SUMS.txt"] != checksums({name: data for name, data in payload.items() if name != "SHA256SUMS.txt"}):
        raise ReleaseError("release checksums differ")
    exported = {}
    for kind in COMPONENTS:
        source = manifest["sources"][kind]
        exact_fields(source, ("version", "commit", "tree", "source_manifest_sha256", "archive"), "source pin")
        full_commit(source["commit"])
        exported[kind] = read_archive(kind, payload[ARCHIVES[kind]])
        expected = {"version": COMPONENTS[kind][1], "archive": ARCHIVES[kind],
                    "tree": tree_hash(exported[kind]),
                    "source_manifest_sha256": verify_source_bytes(kind, exported[kind])}
        check_values(source, expected, "source pin")
    if payload["START-HERE.md"] != start_here(manifest["sources"]):
        raise ReleaseError("handoff instructions differ from the source cohort")
    return exported, manifest


def smoke_initializer(exported):
    # Only verified regular members are written; ZipFile.extract is never used.
    with tempfile.TemporaryDirectory(prefix="asteach-release-verify-") as temporary:
        base = Path(temporary).resolve()
        app = base / "asTeach-App"
        identity = {"device": base.stat().st_dev, "inode": base.stat().st_ino}
        init.create_exclusive(app, exported["app"], identity)
        script = app / "scripts/course_init.py"
        environment = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        def run(*args):
            result = subprocess.run([sys.executable, "-B", str(script), *args], cwd=base,
                                    env=environment, text=True, capture_output=True)
            if result.returncode:
                raise ReleaseError("unpacked initializer failed: " + result.stderr.strip())
            return parse_json(result.stdout)
        run("verify")
        docs_result = subprocess.run([sys.executable, "-B", str(app / "scripts/check_docs.py")],
                                     cwd=base, env=environment, text=True, capture_output=True)
        if docs_result.returncode or parse_json(docs_result.stdout).get("status") != "pass":
            raise ReleaseError("unpacked user guide check failed: " + docs_result.stderr.strip())
        target = str(base / "fresh course")
        plan = run("plan", "--destination", target)
        applied = run("apply", "--destination", target, "--plan-id", plan["plan_id"])
        replayed = run("apply", "--destination", target, "--plan-id", plan["plan_id"])
        checked = run("check", "--destination", target)
        if applied["writes"] != 19 or replayed["writes"] != 0 or checked["status"] != "unchanged":
            raise ReleaseError("unpacked initializer behavior differs")


def verify_bundle(bundle):
    bundle = init.inspect_path(bundle)
    files, directories = init.tree_inventory(bundle)
    if "RELEASE-MANIFEST.json" in files:
        metadata = parse_json(init.read_regular(bundle / "RELEASE-MANIFEST.json"))
        if isinstance(metadata, dict) and metadata.get("schema") == "asteach-release/v1":
            raise ReleaseError(LEGACY_MESSAGE)
    if files != set(BUNDLE_FILES) or directories:
        raise ReleaseError("bundle must contain exactly four files and no directories")
    payload = {name: init.read_regular(bundle / name) for name in BUNDLE_FILES}
    exported, manifest = verify_bundle_bytes(payload)
    smoke_initializer(exported)
    return {"status": "verified", "native_acceptance": "pending", "publication": "pending",
            "sources": manifest["sources"], "files": len(payload), "initializer": "verified"}


def output_path(parent, name, roots):
    parent = init.inspect_path(parent)
    if not parent.is_dir() or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", name):
        raise ReleaseError("output needs an existing parent and a simple new directory name")
    target = init.inspect_path(parent / name, allow_missing=True)
    for root in roots:
        root = init.inspect_path(root)
        if target == root or target in root.parents or root in target.parents:
            raise ReleaseError("output must not overlap either source root")
    if os.path.lexists(target):
        raise ReleaseError("output already exists; choose a new release directory")
    return target


def build(app_root, app_commit, output_parent, output_name):
    roots = {"app": init.inspect_path(app_root)}
    target = output_path(output_parent, output_name, roots.values())
    identity = {"device": target.parent.stat().st_dev, "inode": target.parent.stat().st_ino}
    commits = {"app": app_commit}
    payloads, sources = {}, {}
    for kind in COMPONENTS:
        payloads[kind], sources[kind] = pinned_source(roots[kind], commits[kind], kind)
    payload = assemble(payloads, sources)
    exported, _ = verify_bundle_bytes(payload)
    smoke_initializer(exported)
    # Reconcile again after assembly, before any output writes.
    for kind in COMPONENTS:
        if pinned_source(roots[kind], commits[kind], kind) != (payloads[kind], sources[kind]):
            raise ReleaseError("source changed while assembling the release")
    init.create_exclusive(target, payload, identity)
    return {"status": "created", "destination": str(target), "sources": sources,
            "files": len(payload), "native_acceptance": "pending", "publication": "pending"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("build", help="build exact clean source pins into a fresh directory")
    for name in ("app-root", "app-commit", "output-parent", "output-name"):
        command.add_argument("--" + name, required=True)
    command.add_argument("--docs-root", help=argparse.SUPPRESS)
    command.add_argument("--docs-commit", help=argparse.SUPPRESS)
    command = commands.add_parser("verify", help="verify a complete bundle and its unpacked initializer")
    command.add_argument("--bundle", required=True)
    command = commands.add_parser("refresh-app-manifest", help="refresh an explicitly edited positive App source inventory")
    command.add_argument("--app-root", required=True)
    command = commands.add_parser("refresh-user-manifest", help="refresh the explicitly reviewed integrated guide inventory first")
    command.add_argument("--app-root", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            if args.docs_root is not None or args.docs_commit is not None:
                raise ReleaseError("Two-root builds are legacy v1. Use the original pinned v1 builder for old sources; v2 builds only the integrated App.")
            result = build(args.app_root, args.app_commit, args.output_parent, args.output_name)
        elif args.command == "verify":
            result = verify_bundle(args.bundle)
        elif args.command == "refresh-user-manifest":
            result = refresh_user_manifest(args.app_root)
        else:
            result = refresh_app_manifest(args.app_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ReleaseError, OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
