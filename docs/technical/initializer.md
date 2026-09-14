# Optional initializer — App v0.1

[START-HERE](../../START-HERE.md) is the command reference. The initializer supports
macOS and Linux with Python 3.9+; its standard library is the only runtime
dependency. Exclusive directory operations are required for safe creation.
A downloaded source package
needs no maintainer checkout, Git executable or network. Manual setup is equally
supported.

`verify` checks the exact positive App inventory in APP-MANIFEST.json, regular
file types, sizes and SHA-256 hashes. Only a source checkout's root `.git` metadata
is ignored without reading it; it is never copied or part of the distribution.
The manifest explicitly excludes itself to
avoid a circular hash; an outer trusted archive checksum covers it. The manifest
and executable must both come from a trusted source. This is integrity checking,
not a signature or authenticity system.

`plan` is read-only. It requires an absent destination and an existing parent.
Its deterministic `plan_id` binds the absolute destination, parent directory
identity, complete manifest hash, template payload and all twenty file writes.
The source manifest uses `asteach-app-source/v3`, `release-candidate` status and
`external-release-manifest` commit binding. It has no own-commit field. The
cohort's external RELEASE-MANIFEST.json records the exact App source commit,
tree hashes and archive hashes, independently of source content. Native acceptance
and publication remain pending. The initializer works from that committed source
or its identical extracted archive without Git or a local ownership database.

`apply` recomputes that plan from freshly verified source and accepts only its
exact SHA-256 identifier. It creates one new workspace containing the MIT license
and minimal root instructions, with seventeen files in `course/`. It refuses source
overlap, symlink paths, existing changed files, partial workspaces and stale plans.
Files are created exclusively; there is no replacement or merge path.
An identical completed replay is a read-only no-op. Retain the original package
if you need to recheck or repeat that exact plan.

`check` is read-only and compares the destination with the distributed blank
workspace. Its output lists missing, changed and additional files; authored drift
after editing is expected and is not a teaching-content error. It never adopts,
repairs, restores or deletes. A course repository's later `.git` metadata is not
inspected; it is reported as an additional directory. Symlinks in course content
are refused. New course assets and edits belong to the instructor.

If a failure or interruption leaves a partial destination, preserve it. `apply`
will refuse to fill it in. Verify the original App and choose another absent
destination for a clean recovery copy, then manually compare any authored work.
Recovery does not require machine state, a receipt, Git or an ownership database.
The plan prints local paths for your review; they are not copied into the course.

Exit codes: `0` successful verification/plan/application or unchanged check;
`1` check found drift; `2` invalid input, source, path, plan or operational error.
No command creates a repository, remote, Space, mapping or publication. Hosted
workflow acceptance remains separate from these local filesystem guarantees.
