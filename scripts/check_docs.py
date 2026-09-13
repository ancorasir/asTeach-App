#!/usr/bin/env python3
"""Check the integrated user guide in App source or an unpacked copy; no writes or network."""
# SPDX-License-Identifier: CC-BY-4.0
# Adapted 2026-09-14 from the asTeach Docs v0.1.1 checker (667da2dc848774dda6aa556ad68740987b08c190).
# Original creator: SONG Chaoyang (songcy@ieee.org), Design and Learning Research Group (https://AncoraSIR.com).
# Changes: integrated App/guide roots, exact nested inventory, approved entry links and duplicate-key checks.
# Full notice and terms: ../docs/user/LICENSE.md and ../docs/user/LICENSES/CC-BY-4.0.txt.
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

APP_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("guide_initializer", APP_ROOT / "scripts/course_init.py")
init = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(init)
ROOT = APP_ROOT / init.USER_ROOT
MANIFEST = "DOCS-MANIFEST.json"
CREATOR = ("SONG Chaoyang (songcy@ieee.org) @ Design and Learning Research Group "
           "(https://AncoraSIR.com)")
CREATOR_MARKDOWN = ("SONG Chaoyang ([songcy@ieee.org](mailto:songcy@ieee.org)) @ "
                    "Design and Learning Research Group "
                    "([https://AncoraSIR.com](https://AncoraSIR.com))")
EXPECTED_PAGES = set(init.USER_PAGES)
EXPECTED_ASSETS = set(init.USER_ASSETS)
EXPECTED_FILES = set(init.USER_FILES)
EXPECTED_MANIFEST_METADATA = init.user_metadata()
EXPECTED_VERSION = init.user_version()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def contained(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def check_metadata(manifest, version):
    require(isinstance(manifest, dict), "Inventory must be an object")
    require(set(manifest) == set(EXPECTED_MANIFEST_METADATA) | {"files"},
            "Unexpected inventory metadata fields")
    for key, value in EXPECTED_MANIFEST_METADATA.items():
        require(type(manifest[key]) is type(value) and manifest[key] == value,
                "Unexpected inventory metadata: " + key)
    require(isinstance(version, dict) and set(version) == set(EXPECTED_VERSION),
            "Unexpected version metadata fields")
    for key, value in EXPECTED_VERSION.items():
        require(type(version[key]) is type(value) and version[key] == value,
                "Unexpected version metadata: " + key)


def check():
    init.inspect_path(ROOT)
    actual, directories = init.tree_inventory(ROOT)
    require(actual == EXPECTED_FILES | {MANIFEST} and
            directories == init.parent_paths(actual), "User guide inventory mismatch")
    manifest = json.loads(init.read_regular(ROOT / MANIFEST), object_pairs_hook=init.reject_duplicates)
    version = json.loads(init.read_regular(ROOT / "VERSION.json"), object_pairs_hook=init.reject_duplicates)
    check_metadata(manifest, version)
    records = manifest["files"]
    require(isinstance(records, list), "Inventory files must be a list")
    for record in records:
        require(isinstance(record, dict) and
                set(record) == {"path", "sha256", "size", "mode"},
                "Unexpected inventory record fields")
        require(isinstance(record["path"], str) and
                isinstance(record["sha256"], str) and
                re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is not None and
                type(record["size"]) is int and record["size"] >= 0 and
                record["mode"] == "0644", "Malformed inventory record")
    expected = [r["path"] for r in records]
    require(len(expected) == len(set(expected)), "Duplicate inventory paths")
    require(expected == sorted(EXPECTED_FILES), "Unexpected source file inventory")
    actual = set()
    for directory, dirs, files in os.walk(ROOT, followlinks=False):
        parent = Path(directory)
        for name in dirs + files:
            path = parent / name
            require(not path.is_symlink(), "Symlink is not allowed: " + str(path))
        for name in files:
            path = parent / name
            require(path.is_file(), "Non-regular file is not allowed: " + str(path))
            actual.add(path.relative_to(ROOT).as_posix())
    require(actual == set(expected) | {MANIFEST}, "File inventory mismatch")
    for record in records:
        relative = record["path"]
        path = ROOT / relative
        require(not Path(relative).is_absolute() and ".." not in Path(relative).parts,
                "Unsafe inventory path")
        require(contained(path.resolve(), ROOT), "Inventory path escapes root")
        data = path.read_bytes()
        require(len(data) == record["size"], "Size mismatch: " + relative)
        require(hashlib.sha256(data).hexdigest() == record["sha256"],
                "Hash mismatch: " + relative)
        mode = format(stat.S_IMODE(path.stat().st_mode), "04o")
        require(mode == record["mode"], "Mode mismatch: " + relative)

    docs = ROOT
    pages = {p.name for p in docs.glob("*.md")} - {"SUMMARY.md", "LICENSE.md", "CHANGELOG.md"}
    require(pages == EXPECTED_PAGES, "Expected exactly ten guide pages")
    summary = (docs / "SUMMARY.md").read_text(encoding="utf-8")
    nav = re.findall(r"\]\(([^)]+)\)", summary)
    require(len(nav) == 10 and set(nav) == EXPECTED_PAGES, "Navigation mismatch")
    require((docs / ".gitbook.yaml").read_text(encoding="utf-8").startswith(
        "root: ./\n"), "Guide configuration must be self-contained")
    require(not (APP_ROOT / ".gitbook.yaml").exists(), "Ambiguous App-root config")
    media = json.loads((docs / "assets/manifest.json").read_text(encoding="utf-8"),
                       object_pairs_hook=init.reject_duplicates)
    require(media["status"] == "release-candidate", "Unexpected media status")
    require(media["native_captures"] == [], "No native captures have been accepted")
    require(len(media["assets"]) == 6, "Expected six schematics")
    asset_paths = {a["path"] for a in media["assets"]}
    asset_alts = {a["path"]: a["alt"] for a in media["assets"]}
    require(asset_paths == {p.relative_to(ROOT).as_posix()
                             for p in (docs / "assets").glob("*.svg")},
            "SVG inventory mismatch")
    embedded = set()
    local_references = 0
    external_urls = set()
    for relative in expected:
        if not relative.endswith(".md"):
            continue
        page = ROOT / relative
        body = page.read_text(encoding="utf-8")
        if "SONG Chaoyang" in body:
            for line in body.splitlines():
                if "SONG Chaoyang" in line:
                    require(CREATOR_MARKDOWN in line,
                            "Wrong Markdown creator credit: " + str(page))
        # The candidate uses inline Markdown links, without nested destinations.
        for match in re.finditer(r"(!?)\[([^\n]*?)\]\(([^\s)]+)\)", body):
            is_image, label, raw = match.groups()
            target = urlsplit(raw)
            if target.scheme:
                require(not is_image, "Images must ship locally")
                require(target.scheme == "https" or raw == "mailto:songcy@ieee.org",
                        "Unexpected URL scheme or email destination")
                if target.scheme == "https":
                    external_urls.add(raw)
                continue
            require(not target.netloc, "Protocol-relative link is not allowed")
            dest = (page.parent / unquote(target.path)).resolve()
            permitted_app_link = not is_image and dest in {APP_ROOT / "START-HERE.md", APP_ROOT / "LICENSE"}
            require(contained(dest, docs) or permitted_app_link, "Link escapes boundary: " + raw)
            init.inspect_path(page.parent / unquote(target.path))
            require(dest.is_file(), "Missing local link target: " + raw)
            require(not target.fragment, "Unexpected unverified local anchor")
            local_references += 1
            if is_image:
                require(label.strip(), "Image lacks alternative text")
                asset_path = dest.relative_to(ROOT).as_posix()
                require(label == asset_alts.get(asset_path), "Asset alternative text mismatch")
                embedded.add(asset_path)
    require(embedded == asset_paths, "Every schematic must be used exactly by scope")
    for asset in media["assets"]:
        require(asset["alt"] and asset["caption"] and asset["source"],
                "Incomplete media provenance")
        require(asset["creator"] == CREATOR,
                "Wrong creator credit")
        require(asset["kind"] == "original-svg-schematic" and
                asset["native_evidence"] is False, "Unverified native evidence")
        require(asset["license"] == "CC-BY-4.0", "Wrong diagram license")
        require(asset["app_version"] == "v0.1" and asset["docs_version"] == "v0.1.1",
                "Wrong asset version")
        svg = ET.parse(ROOT / asset["path"]).getroot()
        names = {el.tag.split("}")[-1] for el in svg.iter()}
        require({"title", "desc"}.issubset(names), "SVG lacks accessible metadata")
        description = svg.find("{http://www.w3.org/2000/svg}desc")
        require(description is not None and description.text ==
                asset["alt"] + " This is a schematic, not a screenshot.",
                "SVG description and manifest alternative text mismatch")
        require(not names.intersection({"script", "foreignObject", "image"}),
                "Unexpected embedded SVG content")
        require("schematic" in "".join(svg.itertext()).lower(), "SVG must say schematic")
        for el in svg.iter():
            require(not any(k.lower().startswith("on") or k.endswith("href")
                            for k in el.attrib), "Unexpected SVG behavior")
    print(json.dumps({"status": "pass", "inventoried_files": len(records),
                      "guide_pages": len(pages), "schematics": len(asset_paths),
                      "local_references": local_references,
                      "external_urls_to_check": sorted(external_urls),
                      "native_acceptance": "pending"}, indent=2))


if __name__ == "__main__":
    try:
        check()
    except (init.InitError, KeyError, OSError, TypeError, ValueError, ET.ParseError) as exc:
        print("Docs verification failed: " + str(exc), file=sys.stderr)
        sys.exit(1)
