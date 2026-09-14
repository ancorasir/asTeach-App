"""Portable static and dependency contracts for the exact shipped One-Page tree."""

import hashlib
import importlib.util
from pathlib import Path
import re
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/one-page"
SPEC = importlib.util.spec_from_file_location("template_init", ROOT / "scripts/course_init.py")
init = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(init)
HEADINGS = (
    "Course Description", "Teaching Goals", "Learning Outcomes", "Content Summary",
    "Assumed Knowledge", "Co-Requisite Courses", "Course Instructor & Teaching Team",
    "Grading Policy", "Academic Integrity", "University Calendar", "Recommended Textbook(s)",
    "Teaching Schedule", "Important Deadlines",
)


class TemplateTests(unittest.TestCase):
    def test_term_guidance_preserves_entire_fresh_course_payload(self):
        # Frozen before the term/Student guide revision, independently of source
        # manifests. No sample snapshots, policy, changed input body or layout may
        # enter the blank course through this documentation-only revision.
        snapshot, _ = init.verify_app(ROOT)
        payload = init.workspace_payload(snapshot)
        self.assertEqual(len(payload), 20)
        records = [init.record(name, payload[name]) for name in sorted(payload)]
        self.assertEqual(init.digest(init.canonical(records)),
                         "28c8b806ee1eaf9a1eb8566f1fa6961d68e5cb68f687927e4406daeedb0e66a8")

    def test_exact_template_inventory(self):
        files, directories = init.tree_inventory(TEMPLATE)
        self.assertEqual(files, set(init.TEMPLATE_FILES))
        self.assertEqual(len(files), 17)
        self.assertEqual(directories, init.parent_paths(files))

    def test_initialized_workspace_preserves_unaffected_v01_bytes(self):
        # Original App payload, excluding only Home and the updated setup README.
        # This frozen digest guards the other twelve resources, workbook, mapping,
        # navigation, license and root instructions independently of new manifests.
        snapshot, _ = init.verify_app(ROOT)
        payload = init.workspace_payload(snapshot)
        self.assertEqual(len(payload), 20)
        changed = {"README.md", "course/README.md",
                   "course/.gitbook/includes/one-page-co-requisite-courses.md"}
        records = [init.record(name, payload[name]) for name in sorted(payload)
                   if name not in changed]
        self.assertEqual(len(records), 17)
        self.assertEqual(init.digest(init.canonical(records)),
                         "f0994cfd1f156cd78258e40490226974c88b47255cd073c83ebb435b185556ba")

    def test_thirteen_sections_and_thirteen_ordered_includes(self):
        home = (TEMPLATE / "README.md").read_text()
        self.assertEqual(tuple(re.findall(r"^## (.+)$", home, re.M)), HEADINGS)
        includes = re.findall(r'{% include "([^"]+)" %}', home)
        self.assertEqual(includes, [".gitbook/includes/one-page-" + name + ".md" for name in init.RESOURCES])
        self.assertEqual(len(set(includes)), 13)
        snapshot, _ = init.verify_app(ROOT)
        payload = init.workspace_payload(snapshot)
        sections = re.split(r"^## .+\n", home, flags=re.M)[1:]
        for heading, section, name in zip(HEADINGS, sections, includes):
            with self.subTest(heading=heading):
                self.assertEqual(section.strip(), '{% include "' + name + '" %}')
                self.assertTrue((TEMPLATE / name).is_file())
                self.assertEqual(payload["course/" + name], (TEMPLATE / name).read_bytes())

    def test_title_description_layout_and_navigation(self):
        home = (TEMPLATE / "README.md").read_text()
        self.assertIn("# [CourseCode] CourseName\n", home)
        self.assertIn("description: Year Season\n", home)
        self.assertIn("layout:\n  width: wide\n", home)
        self.assertEqual((TEMPLATE / "SUMMARY.md").read_text(), "# Table of contents\n\n* [[CourseCode] CourseName](README.md)\n")
        self.assertEqual((TEMPLATE / ".gitbook.yaml").read_text(), "root: ./\nstructure:\n  readme: README.md\n  summary: SUMMARY.md\n")

    def test_learning_outcomes_and_corequisite_are_guided_reusables(self):
        resource = TEMPLATE / ".gitbook/includes/one-page-learning-outcomes.md"
        body = resource.read_text()
        self.assertTrue(body.startswith("---\ntitle: one-page-learning-outcomes\n---\n\n"))
        self.assertIn("observable action verb", body)
        self.assertIn("- LearningOutcome", body)
        corequisite = (TEMPLATE / ".gitbook/includes/one-page-co-requisite-courses.md").read_text()
        self.assertTrue(corequisite.startswith("---\ntitle: one-page-co-requisite-courses\n---\n\n"))
        self.assertIn("take concurrently", corequisite)
        self.assertIn('"None" only if you have confirmed', corequisite)
        self.assertIn("- CourseCode — CourseTitle", corequisite)
        self.assertNotIn("{% include", corequisite)

    def test_corequisite_body_and_reconstructed_home_preserve_original_bytes(self):
        # Hashes captured before the extraction, independently of refreshed manifests.
        resource = (TEMPLATE / ".gitbook/includes/one-page-co-requisite-courses.md").read_bytes()
        prefix = b"---\ntitle: one-page-co-requisite-courses\n---\n\n"
        self.assertTrue(resource.startswith(prefix))
        body = resource[len(prefix):]
        self.assertEqual(len(body), 267)
        self.assertEqual(init.digest(body),
                         "5a106d2a0919dca1f9bddc5caedbba58f7c44abce9233b5788956b9e686ed7a8")
        home = (TEMPLATE / "README.md").read_bytes()
        directive = b'{% include ".gitbook/includes/one-page-co-requisite-courses.md" %}\n'
        self.assertEqual(home.count(directive), 1)
        self.assertEqual(init.digest(home.replace(directive, body)),
                         "4eaad9f73b92bbfd9fcca6f09d4429cb45f061c7e359dc62cb330c2c102e2613")

    def test_every_resource_identity_unique(self):
        titles = []
        for name in init.RESOURCES:
            text = (TEMPLATE / (".gitbook/includes/one-page-" + name + ".md")).read_text()
            titles.append(re.search(r"^title: (.+)$", text, re.M).group(1))
        self.assertEqual(titles, ["one-page-" + name for name in init.RESOURCES])

    def test_calendar_source_relative_link_stays_in_mapped_tree(self):
        include = TEMPLATE / ".gitbook/includes/one-page-university-calendar.md"
        links = re.findall(r"\]\(([^)]+)\)", include.read_text())
        self.assertEqual(links, ["../assets/calendar-2000-2050.xlsx"])
        target = (include.parent / links[0]).resolve()
        self.assertEqual(target, TEMPLATE / ".gitbook/assets/calendar-2000-2050.xlsx")
        self.assertTrue(target.is_file())

    def test_workbook_original_hash_and_readable_archive(self):
        path = TEMPLATE / ".gitbook/assets/calendar-2000-2050.xlsx"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), "a0811fb64a2d28772a38a753f59bab5eb11f5c6ffff9244e0ebaf3bfa83fe6c3")
        with zipfile.ZipFile(path) as book:
            self.assertIsNone(book.testzip())
            self.assertEqual(len([p for p in book.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", p)]), 51)

    def test_no_private_mapping_or_deep_include_anchors(self):
        for path in TEMPLATE.rglob("*.md"):
            text = path.read_text()
            self.assertNotIn("preparation/", text.lower())
            self.assertNotRegex(text, r"\]\(#[^)]+\)")
            self.assertNotIn("<a ", text)
            self.assertNotIn("github.com", text)

    def test_every_shipped_markdown_file_link_resolves(self):
        # course-template README is a payload file whose links resolve after copying.
        snapshot, _ = init.verify_app(ROOT)
        payload = init.workspace_payload(snapshot)
        for relative in sorted(name for name in snapshot if name.endswith(".md")):
            path = ROOT / relative
            for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                if "://" in target or target.startswith(("#", "mailto:")):
                    continue
                target = target.split("#", 1)[0]
                with self.subTest(file=relative, target=target):
                    if relative.startswith("course-template/"):
                        self.assertIn(target, payload)
                    else:
                        resolved = (path.parent / target).resolve()
                        self.assertIn(ROOT, resolved.parents)
                        self.assertTrue(resolved.is_file())

    def test_license_credit_and_version_cohort(self):
        self.assertEqual((ROOT / "VERSION").read_text(), "v0.1\n")
        license_text = (ROOT / "LICENSE").read_text()
        self.assertIn("MIT License", license_text)
        self.assertIn("SONG Chaoyang (songcy@ieee.org) @ Design and Learning Research Group (https://AncoraSIR.com)", license_text)
        self.assertIn("THE SOFTWARE IS PROVIDED", license_text)
        self.assertIn("asTeach Docs v0.1.1", (ROOT / "README.md").read_text())
        snapshot, _ = init.verify_app(ROOT)
        self.assertEqual(init.workspace_payload(snapshot)["LICENSE"], (ROOT / "LICENSE").read_bytes())

    def test_contact_credit_and_current_term_are_consistent(self):
        for name in ("README.md", "PROVENANCE.md", "course-template/README.md"):
            text = (ROOT / name).read_text()
            self.assertIn("[songcy@ieee.org](mailto:songcy@ieee.org)", text)
            self.assertIn("[https://AncoraSIR.com](https://AncoraSIR.com)", text)
        for name in ("START-HERE.md", "docs/one-page-course.md"):
            self.assertIn("Year Season", (ROOT / name).read_text())
            self.assertNotIn("Season Year", (ROOT / name).read_text())

    def test_shipped_runtime_has_no_git_or_network_execution(self):
        source = (ROOT / "scripts/course_init.py").read_text()
        for forbidden in ("import subprocess", "import socket", "import urllib", "import requests", "os.system("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
