# Offline release packaging

The developer builder creates a private release-candidate cohort from App v0.1
and Docs v0.1.1. Native GitBook acceptance and publication remain pending. It
does not create repositories, commits, tags, releases, mappings or access changes.
Ordinary course creation uses the [initializer](initializer.md) or manual copying.

## Prepare reviewed sources

Use Python 3.9+ on macOS or Linux and a Git installation supporting
`rev-parse --show-object-format`. No third-party Python packages or network are
needed. Each source must be the root of its own independent, non-overlapping
Git working tree with a real `.git/` directory and a complete local object store.
Linked worktrees, shared Git metadata, alternate object stores, symlinks,
partial/promisor object stores, submodules and executable source files are
refused. Internal Git metadata is inspected for symlinks before Git reads it.
Regular source files use
Git mode `100644` and working-file/archive mode `0644`. Working file permissions,
including each manifest, are checked even when Git has `core.filemode=false`.

After an authorized App edit, refresh its source manifest explicitly:

```bash
python3 -B scripts/package_release.py refresh-app-manifest --app-root /absolute/path/to/asTeach-App
python3 -B scripts/course_init.py verify
python3 -B -m unittest discover -s tests -p 'test_*.py'
```

Manifest refresh accepts only the complete positive App inventory. An unknown
file or directory is a stop; preserve it and inspect its ownership. Refreshing a
manifest is not source review or approval. Review and commit each source through
the separately authorized development workflow. The builder never repairs dirty
sources or makes commits. Run the matching Docs checker before its commit.

App source uses `asteach-app-source/v2`; Docs uses `schema_version: 2` in
DOCS-MANIFEST.json and VERSION.json. Both declare `release-candidate` and
`external-release-manifest` commit binding. Their own Git identities appear only
in the external cohort manifest after committing; no source file must contain
its own future commit hash. Source manifests exclude only themselves explicitly.

## Build the paired cohort

Choose an existing output parent outside both source trees and a new simple
child name. Replace the uppercase commit placeholders with exact lowercase
40-character commit IDs. Branch names, tags and abbreviations are not accepted.

```bash
python3 -B scripts/package_release.py build \
  --app-root /absolute/path/to/asTeach-App \
  --app-commit APP_FULL_40_HEX_COMMIT \
  --docs-root /absolute/path/to/asTeach-Docs \
  --docs-commit DOCS_FULL_40_HEX_COMMIT \
  --output-parent /absolute/path/to/release-output \
  --output-name private-v0.1
```

Both current HEADs must equal the requested pins. The builder compares the raw
Git index with the committed tree and checks working, untracked and ignored
extras; validates every file against the fixed
positive inventories and source manifests; reads exact Git blob/tree objects;
and compares exported bytes with the worktrees. It checks the sources again
after assembly before creating the output. History, `.git`, private records and
unlisted files never enter the archives. SHA-1 identifies Git objects; SHA-256
protects source and asset integrity. A checksum is not a publisher signature.
The builder does not invoke Git status or working-file conversion filters, and
refuses partial repositories so reading missing objects cannot trigger a fetch.

The output contains exactly five files:

| File | Purpose |
| --- | --- |
| `asTeach-App-v0.1.zip` | Complete App source under `asTeach-App/` |
| `asTeach-Docs-v0.1.1.zip` | Complete matched Docs source under `asTeach-Docs/` |
| `START-HERE.md` | Portable handoff with exact source commits |
| `RELEASE-MANIFEST.json` | Actual App/Docs commits, exported tree hashes, source manifest hashes, asset hashes and pending acceptance status |
| `SHA256SUMS.txt` | SHA-256 of the other four files |

The release manifest's asset inventory covers both ZIPs and START-HERE.md. It
explicitly excludes itself and SHA256SUMS.txt to avoid circular hashes; the
checksum file covers RELEASE-MANIFEST.json. Retain the complete bundle and a
trusted publisher checksum record. Git pins are validated when building; an
offline recipient checks the exported trees against that supplied record, not
remote repository ownership or publisher authenticity.

ZIP entries are sorted regular files, use fixed 1980 timestamps and stored
compression, and carry no variable host paths or build times. Rebuilding the
same source commits produces byte-identical files regardless of output name.
The builder accepts no public-release or native-accepted mode.

## Verify and recover without maintainer state

From a trusted extracted App source, run:

```bash
python3 -B scripts/package_release.py verify --bundle /absolute/path/to/release-output/private-v0.1
```

This command needs no Git executable, repository history, network, original
source path, machine ownership state or receipt. It verifies the five-file
inventory, JSON schemas, checksums, canonical archives, complete source
inventories, source versions and reconstructed Git tree hashes. It extracts only
verified regular App files to temporary storage, then runs that App's initializer
through verify, plan, apply, identical replay and check on a fresh disposable
course. It does not claim native GitBook acceptance or run the Docs GUI workflow.

Build refuses an existing destination, including an empty directory, and never
overwrites or deletes it. If an interrupted write leaves a partial output,
preserve it for inspection and build to another new child name. Input sources
are never modified by build/verify; manifest refresh is the explicit developer
write command. Exit code `0` means success; `2` means invalid input, integrity,
path, source pin or operational failure. Preserve any partial output after failure.
