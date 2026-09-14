#!/usr/bin/env python3
"""Verify and copy the reviewed blank course into a fresh local workspace."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

VERSION = "v0.1"
DOCS_VERSION = "v0.1.1"
CREATOR = "SONG Chaoyang (songcy@ieee.org) @ Design and Learning Research Group (https://AncoraSIR.com)"
MANIFEST = "APP-MANIFEST.json"
USER_ROOT = "docs/user"
USER_MANIFEST = "DOCS-MANIFEST.json"
USER_PAGES = (
    "README.md", "getting-started.md", "setup-gitbook.md", "one-page-course.md",
    "course-home-reference.md", "schedule-and-deadlines.md", "calendar-and-files.md",
    "review-and-sharing.md", "troubleshooting.md", "version-and-scope.md",
)
USER_ASSETS = (
    "01-course-overview.svg", "02-setup-mapping.svg", "03-resource-ownership.svg",
    "04-title-description.svg", "05-calendar-alt.svg", "06-save-review.svg",
)
USER_FILES = tuple(sorted(USER_PAGES + (
    ".gitbook.yaml", "SUMMARY.md", "assets/manifest.json", "LICENSE.md",
    "LICENSES/CC-BY-4.0.txt", "VERSION.json", "CHANGELOG.md",
) + tuple("assets/" + name for name in USER_ASSETS)))
RESOURCES = (
    "course-description", "teaching-goals", "learning-outcomes", "content-summary",
    "assumed-knowledge", "co-requisite-courses", "teaching-team", "grading-policy", "academic-integrity",
    "university-calendar", "textbooks", "teaching-schedule", "important-deadlines",
)
TEMPLATE_FILES = tuple(sorted((
    ".gitbook.yaml", "README.md", "SUMMARY.md",
    ".gitbook/assets/calendar-2000-2050.xlsx",
) + tuple(".gitbook/includes/one-page-" + name + ".md" for name in RESOURCES)))
APP_FILES = tuple(sorted((
    ".gitignore", "AGENTS.md", "README.md", "START-HERE.md", "LICENSE",
    "VERSION", "CHANGELOG.md", "PROVENANCE.md", "course-template/README.md",
    "course-template/AGENTS.md", "docs/one-page-course.md", "docs/initializer.md",
    "scripts/course_init.py", "scripts/package_release.py", "docs/release-packaging.md",
    "docs/technical/one-page-course.md", "docs/technical/initializer.md",
    "docs/technical/release-packaging.md", "scripts/check_docs.py", "tests/test_docs.py",
    "tests/test_course_init.py", "tests/test_template.py", "tests/test_package_release.py",
) + tuple("templates/one-page/" + path for path in TEMPLATE_FILES)
  + tuple(USER_ROOT + "/" + path for path in USER_FILES + (USER_MANIFEST,))))


class InitError(Exception):
    """An unsafe, stale or unsupported local operation."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def record(path, data):
    return {"path": path, "size": len(data), "sha256": digest(data)}


def app_metadata():
    return {"schema": "asteach-app-source/v3", "app_version": VERSION,
            "docs_version": DOCS_VERSION, "status": "release-candidate",
            "commit_binding": "external-release-manifest", "manifest_self_exclusion": MANIFEST,
            "license": "MIT", "license_overrides": {USER_ROOT + "/": "CC-BY-4.0",
                                                       "scripts/check_docs.py": "CC-BY-4.0"}}


def user_metadata():
    return {"schema_version": 3, "component": "asTeach-User-Guide",
            "status": "release-candidate", "docs_version": DOCS_VERSION,
            "app_version": VERSION, "commit_binding": "external-release-manifest",
            "content_root": USER_ROOT + "/", "license": "CC-BY-4.0", "creator": CREATOR,
            "self_excluded": [USER_MANIFEST]}


def user_version():
    return {"schema_version": 3, "component": "asTeach-User-Guide", "docs_version": DOCS_VERSION,
            "for_app_version": VERSION, "creator": CREATOR, "status": "release-candidate",
            "commit_binding": "external-release-manifest", "native_acceptance": "pending",
            "license": "CC-BY-4.0", "content_root": USER_ROOT + "/",
            "guide_page_count": 10, "schematic_figure_count": 6}


def verify_user_source(payload):
    """Check the guide component independently within the positive App payload."""
    prefix = USER_ROOT + "/"
    guide = {name[len(prefix):]: data for name, data in payload.items() if name.startswith(prefix)}
    if set(guide) != set(USER_FILES) | {USER_MANIFEST}:
        raise InitError("user guide inventory mismatch")
    try:
        metadata = json.loads(guide[USER_MANIFEST], object_pairs_hook=reject_duplicates)
        version = json.loads(guide["VERSION.json"], object_pairs_hook=reject_duplicates)
    except (ValueError, UnicodeError) as error:
        raise InitError("invalid user guide metadata: " + str(error))
    expected = user_metadata()
    expected["files"] = [dict(record(name, guide[name]), mode="0644") for name in USER_FILES]
    # Canonical bytes distinguish booleans from numbers in nested metadata.
    if canonical(metadata) != canonical(expected) or canonical(version) != canonical(user_version()):
        raise InitError("user guide version, manifest or checksum mismatch")
    return digest(guide[USER_MANIFEST])


def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InitError("duplicate JSON key: " + key)
        result[key] = value
    return result


def safe_relative(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise InitError("invalid payload path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise InitError("payload traversal is not allowed: " + value)
    if any(ord(char) < 32 for char in value):
        raise InitError("control characters in payload path")
    return value


def inspect_path(path, allow_missing=False):
    """Reject every symlink in a local path, before reading or writing it."""
    path = Path(os.path.abspath(os.fspath(path)))
    for current in reversed((path,) + tuple(path.parents)):
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            if allow_missing:
                continue
            raise InitError("missing path: " + str(current))
        if stat.S_ISLNK(mode):
            raise InitError("symlink path refused: " + str(current))
    return path


def read_regular(path):
    path = inspect_path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise InitError("not a regular file: " + str(path))
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise InitError("file changed while opening: " + str(path))
        data = stream.read()
        after = os.fstat(stream.fileno())
    if (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise InitError("file changed while reading: " + str(path))
    return data


def tree_inventory(root, skip_git=False):
    """List types without reading unexpected content or following links."""
    root = inspect_path(root)
    if not root.is_dir():
        raise InitError("not a directory: " + str(root))
    files, directories = set(), set()
    for current, names, filenames in os.walk(root, followlinks=False):
        for name in list(names):
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                raise InitError("unsafe directory: " + relative)
            directories.add(relative)
            if skip_git and relative == ".git":
                names.remove(name)
        for name in filenames:
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            if not stat.S_ISREG(path.lstat().st_mode):
                raise InitError("unsafe file: " + relative)
            files.add(relative)
    return files, directories


def parent_paths(files):
    return {parent.as_posix() for name in files for parent in PurePosixPath(name).parents if str(parent) != "."}


def verify_app(root):
    root = inspect_path(root)
    files, directories = tree_inventory(root, skip_git=True)
    # A source checkout may have opaque root Git metadata. It is never
    # read, hashed, copied or part of the distributable file allowlist.
    files.discard(".git")
    directories.discard(".git")
    expected = set(APP_FILES) | {MANIFEST}
    if files != expected or directories != parent_paths(expected):
        raise InitError("App inventory mismatch (missing, additional or unexpected directory)")
    manifest_bytes = read_regular(root / MANIFEST)
    try:
        metadata = json.loads(manifest_bytes, object_pairs_hook=reject_duplicates)
    except (ValueError, UnicodeError) as error:
        raise InitError("invalid App manifest: " + str(error))
    fields = set(app_metadata()) | {"files"}
    if not isinstance(metadata, dict) or set(metadata) != fields:
        raise InitError("unsupported App manifest fields")
    expected_metadata = app_metadata()
    if any(metadata[key] != value for key, value in expected_metadata.items()):
        raise InitError("unsupported version, status or provenance metadata")
    entries = metadata["files"]
    if not isinstance(entries, list):
        raise InitError("manifest files must be a list")
    paths = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "size", "sha256"}:
            raise InitError("invalid manifest file record")
        paths.append(safe_relative(entry["path"]))
        if type(entry["size"]) is not int or entry["size"] < 0 or not isinstance(entry["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise InitError("invalid manifest size or hash")
    if paths != list(APP_FILES):
        raise InitError("manifest must match the sorted positive App allowlist exactly")
    snapshot = {path: read_regular(root / path) for path in APP_FILES}
    if entries != [record(path, snapshot[path]) for path in APP_FILES]:
        raise InitError("App checksum mismatch; preserve source and obtain a verified package")
    verify_user_source(snapshot)
    return snapshot, digest(manifest_bytes)


def workspace_payload(snapshot):
    payload = {"LICENSE": snapshot["LICENSE"],
               "README.md": snapshot["course-template/README.md"],
               "AGENTS.md": snapshot["course-template/AGENTS.md"]}
    payload.update({"course/" + path: snapshot["templates/one-page/" + path] for path in TEMPLATE_FILES})
    return payload


def destination_path(root, destination):
    if not destination or any(ord(char) < 32 for char in destination):
        raise InitError("invalid destination")
    target = inspect_path(destination, allow_missing=True)
    source = inspect_path(root)
    if target == source or target in source.parents or source in target.parents:
        raise InitError("destination overlaps the App source")
    parent = inspect_path(target.parent)
    if not parent.is_dir():
        raise InitError("destination parent must be an existing directory")
    return target


def make_plan(root, destination, require_absent=True):
    snapshot, manifest_hash = verify_app(root)
    target = destination_path(root, destination)
    if require_absent and os.path.lexists(target):
        raise InitError("destination already exists; choose a new workspace")
    info = target.parent.stat()
    payload = workspace_payload(snapshot)
    plan = {"schema": "asteach-course-init-plan/v1", "status": "planned", "app_version": VERSION,
            "source_manifest_sha256": manifest_hash, "destination": str(target),
            "parent_identity": {"device": info.st_dev, "inode": info.st_ino},
            "mapped_directory": "course/",
            "files": [record(path, payload[path]) for path in sorted(payload)]}
    plan["plan_id"] = digest(canonical(plan))
    return plan, payload


def compare_workspace(target, payload):
    files, directories = tree_inventory(target, skip_git=True)
    expected = set(payload)
    missing = sorted(expected - files)
    changed = sorted(path for path in expected & files if read_regular(target / path) != payload[path])
    extra = sorted((files - expected) | {path + "/" for path in directories - parent_paths(expected)})
    return {"status": "drift" if missing or changed or extra else "unchanged",
            "missing": missing, "changed": changed, "additional": extra}


def create_exclusive(target, payload, identity):
    """Use directory descriptors and exclusive files; never replace a target."""
    required = (os.open, os.mkdir, os.stat)
    if not all(function in os.supports_dir_fd for function in required) or not hasattr(os, "O_NOFOLLOW"):
        raise InitError("safe initialization requires macOS or Linux directory-descriptor support")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    handles = {}
    parent_fd = os.open(target.parent, flags)
    try:
        info = os.fstat(parent_fd)
        if {"device": info.st_dev, "inode": info.st_ino} != identity:
            raise InitError("destination parent changed after planning")
        os.mkdir(target.name, mode=0o755, dir_fd=parent_fd)
        root_fd = os.open(target.name, flags, dir_fd=parent_fd)
        handles[""] = root_fd
        for name in sorted(parent_paths(payload), key=lambda value: (value.count("/"), value)):
            relative = PurePosixPath(name)
            parent_name = str(relative.parent) if str(relative.parent) != "." else ""
            os.mkdir(relative.name, mode=0o755, dir_fd=handles[parent_name])
            handles[name] = os.open(relative.name, flags, dir_fd=handles[parent_name])
        for name in sorted(payload):
            relative = PurePosixPath(name)
            parent_name = str(relative.parent) if str(relative.parent) != "." else ""
            descriptor = os.open(relative.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o644, dir_fd=handles[parent_name])
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload[name])
        if compare_workspace(target, payload)["status"] != "unchanged":
            raise InitError("destination changed during initialization; preserve and inspect it")
    finally:
        for descriptor in handles.values():
            os.close(descriptor)
        os.close(parent_fd)


def apply_plan(root, destination, plan_id):
    if not re.fullmatch(r"[0-9a-f]{64}", plan_id):
        raise InitError("plan_id must be the exact printed SHA-256")
    plan, payload = make_plan(root, destination, require_absent=False)
    if plan_id != plan["plan_id"]:
        raise InitError("stale or unapproved plan; generate and review a fresh plan")
    target = Path(plan["destination"])
    if os.path.lexists(target):
        if compare_workspace(target, payload)["status"] == "unchanged":
            return {"status": "unchanged", "plan_id": plan_id, "writes": 0}
        raise InitError("existing workspace differs; preserve it and choose a new destination")
    try:
        create_exclusive(target, payload, plan["parent_identity"])
    except OSError as error:
        raise InitError("initialization stopped; preserve any partial destination: " + str(error))
    return {"status": "created", "plan_id": plan_id, "writes": len(payload)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="asTeach App " + VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify", help="verify the complete App file allowlist and hashes")
    for name in ("plan", "apply", "check"):
        command = sub.add_parser(name)
        command.add_argument("--destination", required=True, help="fresh workspace root, containing course/")
        if name == "apply":
            command.add_argument("--plan-id", required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).absolute().parents[1]
    try:
        if args.command == "verify":
            snapshot, manifest_hash = verify_app(root)
            result = {"status": "verified", "app_version": VERSION,
                      "source_manifest_sha256": manifest_hash, "files": len(snapshot)}
        elif args.command == "plan":
            result, _ = make_plan(root, args.destination)
        elif args.command == "apply":
            result = apply_plan(root, args.destination, args.plan_id)
        else:
            snapshot, _ = verify_app(root)
            target = destination_path(root, args.destination)
            result = compare_workspace(target, workspace_payload(snapshot))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1 if result["status"] == "drift" else 0
    except (InitError, OSError, ValueError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
