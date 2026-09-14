# Troubleshooting

Docs v0.1.1 · for App v0.1 · release candidate

Preserve your current draft and saved source when a check fails. The initializer
does not repair an edited course; a baseline difference can simply be your work.

| Symptom | Next action and expected result |
| --- | --- |
| Reusable text is read-only | Inspect the resource's parent Space/section and your edit permission. Continue only when it is owned by your course and editable there. |
| A reusable block keeps loading | Wait, reopen the same saved page and inspect its Library entry. Persistent failure or missing ownership means import acceptance has failed. |
| Learning Outcomes still shows guidance or appears empty | The starter contains replaceable guidance. Verify the dedicated resource belongs to this course and is editable, then replace the guidance with your own measurable outcomes. If text is unexpectedly missing, compare the saved source before editing. |
| Co-Requisite Courses has no reusable block | The current candidate requires its own reusable resource. Inspect the source include and destination ownership; preserve authored work and resolve the import before editing. |
| Title or navigation shows the wrong name | Compare the page title, plain description and navigation caption with your intended values and saved source. Preserve the draft if a local/native mismatch exists. |
| Duplicate Home or README conflict | GitBook's current configuration guidance warns about README editing with Git Sync. Stop the container edit, compare draft and saved source, and seek a reviewed correction. Do not rename or flatten to conceal it. |
| Module links do not reach the module | Use Teaching Schedule and scroll. Included module deep links are outside v0.1 scope. |
| Workbook link does not download | Open the included workbook locally. Hosted download remains unverified; add separately tested delivery only if needed. |
| File opens for you but not a reader | Check the file host's access using the intended reader account. Do not change repository visibility to make one link work without reviewing its contents and history. |
| Internal include files appear in navigation | Check the mapped course directory and SUMMARY. Do not accept the import until only the intended Home appears. |
| Initializer reports changed files | Compare with the saved course and your edits. Preserve differences; it has no overwrite or reset workflow. |
| GitHub or GitBook has newer changes | Reconcile the full saved export, repository commit and open drafts before later local edits. Do not replace them with the starter. |

See the current [GitBook content configuration guidance](https://gitbook.com/docs/docs-as-code/git-sync/content-configuration)
for README behavior and [reusable content](https://gitbook.com/docs/create-content/reusable-content)
for ownership rules.

## Report a candidate issue

Use the person or channel that supplied the candidate; no public issue tracker
or support address is announced yet. Include:

- App and Docs versions, source commit pins and the handoff archive digests.
- Which step failed, what you expected, and what you observed.
- Whether you were in a draft, the saved Space or a published reader view.
- Whether the problem repeats after reopening.

Share only a minimal neutral reproduction. Remove account identifiers,
repository/Space IDs, private links, personal records and actual course data
from screenshots or logs. Keep originals privately for your own recovery.
