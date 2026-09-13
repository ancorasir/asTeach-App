# Offline release packaging

The builder creates a private release candidate from App v0.1, including the
Docs v0.1.1 guide under `docs/user/`. Native acceptance and publication remain
pending. Course creation follows [START-HERE](../../START-HERE.md); packaging is
a separate developer operation and creates no repositories, commits, tags,
releases, mappings or access settings.

## Reviewed source and manifests

Use Python 3.9+ on macOS/Linux and Git supporting
`rev-parse --show-object-format`. No third-party Python dependencies or network
are needed. App must be the exact root of an independent Git checkout with a
real `.git/` directory and complete local objects. The builder reads no private
Docs development checkout. Linked worktrees, shared metadata, alternate object
stores, symlinks, submodules, partial/promisor stores and executable source files
are refused. Internal Git metadata is checked for symlinks before Git runs.
All source/archive files use mode `0644` and Git mode `100644`, even when
`core.filemode=false`.

After reviewed guide edits, refresh the guide manifest first, then App's:

```bash
python3 -B scripts/package_release.py refresh-user-manifest --app-root /absolute/path/to/asTeach-App
python3 -B scripts/package_release.py refresh-app-manifest --app-root /absolute/path/to/asTeach-App
python3 -B scripts/course_init.py verify
python3 -B scripts/check_docs.py
python3 -B -m unittest discover -s tests -p 'test_*.py'
```

Refresh accepts only complete positive inventories, and never discovers extra
files as new approved content. An unknown file/directory requires inspection and
preservation. Refresh does not grant source approval. Review and commit through
the authorized development workflow; build never repairs or commits a dirty tree.

App uses `asteach-app-source/v3`; guide manifest/version metadata use schema 3.
Both retain release-candidate status, App v0.1/Docs v0.1.1 and external commit
binding. The guide manifest excludes itself; App's manifest includes it and
excludes only itself. No source file contains its own future commit. App's default
MIT license has explicit CC-BY-4.0 overrides for `docs/user/` and the adapted
`scripts/check_docs.py`. Guide license
notices identify the integration changes and retain original attribution.

## Build one archive

Choose an existing output parent outside the source tree and a new child name.
Supply the exact lowercase forty-character App commit, never a branch, tag or
abbreviation:

```bash
python3 -B scripts/package_release.py build \
  --app-root /absolute/path/to/asTeach-App \
  --app-commit APP_FULL_40_HEX_COMMIT \
  --output-parent /absolute/path/to/release-output \
  --output-name private-v0.1-integrated
```

HEAD must equal the supplied pin. The builder compares the raw index with the
committed tree, checks every working file including ignored/untracked extras,
and validates fixed inventories and hashes. It reads exact Git objects without
working-file conversion filters, reconstructs the exported Git tree hash, and
rechecks the source after assembly before creating output. Partial repositories
are refused so a missing object cannot cause a fetch.

| File | Contents |
| --- | --- |
| `asTeach-App-v0.1.zip` | Complete App, guide and technical documentation under `asTeach-App/` |
| `START-HERE.md` | Portable handoff with the exact App commit |
| `RELEASE-MANIFEST.json` | Release schema v2, App commit/tree, both component versions, source manifest/asset hashes, pending gates |
| `SHA256SUMS.txt` | SHA-256 of the other three files |

The release manifest hashes the ZIP and handoff, and explicitly excludes itself
and the checksum file. The checksum file covers the release manifest. Retain the
complete four-file cohort and a trusted publisher checksum record. Git SHA-1
identifies objects; SHA-256 checks integrity. Neither authenticates the publisher.

ZIP entries are sorted regular files with fixed 1980 timestamps and stored
compression. No host paths, build times, Git metadata or private records enter
the archive. Identical commits produce identical bundles regardless of output
name. The builder has no accepted/public mode. Reviewed candidate files must
already have been promoted into independent App history before a pinned build.

## Portable verification and compatibility

From the trusted extracted App folder:

```bash
python3 -B scripts/package_release.py verify --bundle /absolute/path/to/release-output/private-v0.1-integrated
```

Verification needs no Git executable, network, private Docs checkout, source
history, machine ownership database or maintainer receipt. It checks the exact
four-file inventory, schemas, versions, checksums, canonical archive and
reconstructed Git tree. Only verified regular members are written to temporary
storage. The included initializer runs verify/plan/apply/replay/check on a fresh
course, and the included guide checker validates its pages/assets. These checks
do not establish native GitBook rendering, edit/export fidelity or reader access.

Earlier `asteach-release/v1` cohorts remain immutable five-file bundles. Verify
them with the trusted `scripts/package_release.py` included in their original
App ZIP; retain the original separate Docs ZIP and all three handoff files.
The new verifier identifies v1 and gives this recovery instruction. New build
rejects legacy two-root flags explicitly; it never silently drops a Docs input.

Initializer commands and the nineteen-file workspace output are unchanged.
Pending old plans require their original App package, or a fresh plan from the
new package for a new absent destination. Manifest binding is not relaxed.

Use a new cohort directory because the App ZIP basename remains v0.1. Never
replace an old archive or infer identity from its filename. App's GitBook
template mapping remains `templates/one-page/`; each initialized course maps
only `course/`. Guide hosting is separate and is not changed by packaging.

Build refuses every existing destination, including an empty directory.
Interrupted output is preserved; inspect it and build into another new child.
Build/verify never modify inputs. Manifest refresh is an explicit developer write.
Exit 0 is success; exit 2 indicates invalid input, integrity, path, pin or
operational failure.
