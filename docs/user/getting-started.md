# Before You Start

Docs v0.1.1 · for App v0.1

You need the matching App release, permission to create and edit a restricted
GitBook Space, and a GitHub account able to host your course repository and
authorize its GitBook connection. Keep your course restricted while checking
the first import. GitBook may use “section” for the content container that owns
reusable resources; this guide uses “course Space” for the destination you select.

For a graphical repository workflow, GitHub Desktop can create, commit and
publish a repository. Its [official first-repository guide](https://docs.github.com/en/desktop/overview/creating-your-first-repository-using-github-desktop)
covers installation and authentication. The local initializer is optional and
supports macOS or Linux with Python 3.9 or later, with no additional Python
packages. Manual copying is platform-independent. An agent is optional help
with setup.

Obtain the matching release handoff: `asTeach-App-v0.1.zip`,
`START-HERE.md`, `RELEASE-MANIFEST.json` and
`SHA256SUMS.txt`. Follow that `START-HERE.md` to verify the bundle before setup.
The external manifest records the exact integrated App source commit, both
versions and the archive digest. The user guide is included at `docs/user/`.
Source inventories identify their contents without
embedding their own Git commit. Check the checksums against the handoff from
your trusted supplier; a matching hash alone does not identify the sender.
Stop if a required file or commit pin is missing, or versions or digests differ.
Download the four files from the [official v0.1 release](https://github.com/ancorasir/asTeach-App/releases/tag/v0.1).
The public product repository is not your private course-authoring repository.

## What belongs where

| Item | Purpose |
| --- | --- |
| Extracted asTeach-App | Reusable source distribution; keep an unchanged copy. |
| Your new course workspace | Your repository: root license and instructions, with mapped content inside `course/`. |
| Your course Space | Your editable Home and its own reusable resources. |
| This guide | Instructions for the template; no second form to fill in. |
| Separate private planning | Personal notes or other restricted work, outside this course repository and mapping. |

The initial course payload has seventeen files: Home, navigation, GitBook
configuration, thirteen reusable Markdown files and one calendar workbook.
The initializer adds three workspace-root files outside `course/`: a license,
README and AGENTS. These are setup/reuse records, not course pages.

The template does not supply real teaching content. Learning Outcomes and
Co-Requisite Courses begin with concise, replaceable guidance and placeholder
bullets. Replace all visible guidance with your own confirmed course information,
or remove it, before sharing.

Continue to [Set Up Your Course](setup-gitbook.md).
