# Start here — App v0.1

This release includes [asTeach Docs v0.1.1](docs/user/README.md).
The external cohort RELEASE-MANIFEST.json binds the exact integrated App commit
and archive hash.
Use the [official v0.1 release](https://github.com/ancorasir/asTeach-App/releases/tag/v0.1)
and compare its exact tag, manifest and checksums. Native acceptance is a
maintainer attestation about the tested template, not your new destination.
Keep the original App package and its checksum for recovery.

## Create a fresh course

The resulting workspace contains `LICENSE`, `README.md` and `AGENTS.md` at its
root, with all seventeen mapped course files under `course/`. Only `course/` is
mapped to GitBook. Keep its hidden `.gitbook/` folder and `.gitbook.yaml` file.

For a manual setup, create a new empty workspace, copy this App's `LICENSE` and
the two files in `course-template/` to its root, then copy all contents of
`templates/one-page/` into a new `course/` folder. Do not copy into an existing
course. You can do this with a file manager; no agent or Python is required.

For the optional initializer on macOS or Linux, install Python 3.9 or later and
open a terminal in the extracted `asTeach-App` folder. The parent directory of your destination must
already exist. Choose a new workspace name; `../my-course` below is a placeholder.

```bash
python3 -B scripts/course_init.py verify
python3 -B scripts/course_init.py plan --destination ../my-course
```

Read the printed destination and all twenty proposed files. Copy the printed
`plan_id` exactly into the following command, replacing `PASTE_PLAN_ID_HERE`:

```bash
python3 -B scripts/course_init.py apply --destination ../my-course --plan-id PASTE_PLAN_ID_HERE
python3 -B scripts/course_init.py check --destination ../my-course
```

`plan` and `check` are read-only. `apply` accepts only that exact plan and verified
source. An identical replay does nothing. It refuses an existing changed or
partial workspace and never repairs, adopts or overwrites it. These commands
create no Git history, remotes, accounts, Spaces or access settings.

## Open and edit the course

Use your own new private repository for the workspace. In a new restricted
GitBook Space, select that repository and its intended branch, set the project
directory to `course/`, and use the repository as the initial source. Account,
repository and GitBook setup are separate user-controlled steps. Follow the
matched [Docs guide](docs/user/setup-gitbook.md) for the walkthrough and verify the actual mapping before use.
The App package itself is never the course mapping.

Check Product Docs presentation at default width, the course title, plain term
description, all thirteen headings and thirteen
independent reusable resources before editing. Change `[CourseCode] CourseName`
in Home and its SUMMARY navigation label together; change `Year Season` in the
description. Learning Outcomes and Co-Requisite Courses each have their own
reusable resource with brief replaceable guidance and a bullet placeholder.
Replace the visible guidance
with your own course information. See [the section contract](docs/technical/one-page-course.md).

The calendar link resolves from its include to the workbook inside the course
folder. Download a local copy, customize it, insert your own approved screenshots
with meaningful alternative text, and remove the temporary guidance and workbook
link when ready. Check actual GitBook download behavior in the intended audience's
view; local file verification does not prove a native attachment or public download.

Save changes, inspect the saved Home and intended reader view, and resolve all
placeholder text and sharing choices before sharing. Course-only source does not
set a Space's visibility. See the matched guide for save and sharing checks.

## Preserve later edits

Keep one private Teacher Home with all thirteen reusable inputs. Fresh courses use
Product Docs presentation at default width. For each `Year Season`, manually prepare an ordinary
term snapshot with no reusable includes. Historical term and independent Student
pages use Docs presentation at default width. Remove a whole term section only
when its complete answer is the confirmed literal `None`; preserve that Teacher
input. Supply no missing facts or policies, including late-submission rules.
Review the [term and Student workflow](docs/user/one-page-course.md),
[calendar ownership](docs/user/calendar-and-files.md) and
[complete saved-result checks](docs/user/review-and-sharing.md) before transfer.
The optional initializer does not perform these later steps.
Existing courses retain their saved layout until a separately reviewed change;
the initializer does not update them.

After editing, `check` reports changed, missing or additional files as authored
drift. It does not validate teaching content or repair anything. Keep your course's
own backups/history. If initialization is interrupted, preserve that partial
workspace and use the original verified App to plan a different fresh destination.
Compare and recover authored content manually. See [initializer limits](docs/technical/initializer.md).

To verify the local product itself:

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py'
python3 -B scripts/check_docs.py
```

The developer [release packaging guide](docs/technical/release-packaging.md) explains the
separate offline builder and portable bundle verification.
