# Source provenance — App v0.1 candidate

Creator: SONG Chaoyang ([songcy@ieee.org](mailto:songcy@ieee.org)) @ Design and Learning Research Group ([https://AncoraSIR.com](https://AncoraSIR.com)).
Prepared 2026-09-13; integrated distribution revised 2026-09-14.
App v0.1 includes asTeach Docs v0.1.1.

The integration starts from App commit
`a735bf349d14d146ae6936441ff1cde890ffee98` and the user guide from
`667da2dc848774dda6aa556ad68740987b08c190`. These are historical origins, not
the new source's own commit or a claim that changed files retain old hashes.
The guide's pages, local schematics, attribution and full license have been
integrated under `docs/user/`; paths, metadata and packaging prose were revised.
That integration retained the original schematic and legal-code bytes. App
technical guides moved to `docs/technical/` with references at their previous
paths; the course template and nineteen-file workspace were then byte-identical.

The subsequent 2026-09-14 unreleased correction moves the existing Co-Requisite
Courses body verbatim from Home into its own titled reusable resource. All
thirteen sections now have includes; the mapped template has seventeen files
and initialization creates twenty. The other twelve resource files, calendar,
navigation, configuration and workspace license/instructions are unchanged;
the workspace README and current guides/schematics describe the revised contract.
The preserved 267-byte Co-Requisite body has SHA-256
`5a106d2a0919dca1f9bddc5caedbba58f7c44abce9233b5788956b9e686ed7a8`.
App v0.1 and guide v0.1.1 remain unreleased candidates, with exact bytes identified
by their refreshed manifests and later external source pin.

This release-candidate source was prepared without copied Git history.
APP-MANIFEST.json records every source payload file's size and SHA-256 and
explicitly excludes itself. It has no own-commit or baseline-commit requirement.
An external RELEASE-MANIFEST.json records the exact integrated App commit, exported Git
tree hash and archive hash after the source is committed. This avoids a
circular requirement for a source commit to contain its own hash. Source changes
require refreshed manifests and review before another pinned build. Native
acceptance, tags and publication remain separate pending gates.

The template was selected from the preserved development working tree based on
commit `0b45a4521a12f8b9111376dc2889aa1d359da0de`, including the uncommitted
Learning Outcomes correction. That commit identifies provenance, not these new
candidate bytes. The initial candidate retained fifteen selected course files
exactly; its sixteenth file, SUMMARY.md, removed Private Notes/Preparation
navigation. The subsequent founder-approved local feedback revision changes
Home's term to Year Season, adds Co-Requisite Courses guidance, and fills the
existing Learning Outcomes resource with replaceable guidance. Thirteen mapped
files still match the preserved source exactly; Home, Learning Outcomes and
SUMMARY are the three deliberately revised files.
The source Preparation page is excluded and preserved in the original development
tree. No actual course or private development record is included.

The previous SUMMARY.md SHA-256 was
`09a6995780ab1db34ddc2086e1a77e42e7f9bf7df06f87bbb74655abbf9ad86a`.
The historical empty Learning Outcomes source was 43 bytes with SHA-256
`0fa85316c975487c32740d3bc1035becb8d910279ea37ac2e864c74591fee33a`.
That historical hash does not describe the current guided resource. Current
file hashes appear under their exact paths in APP-MANIFEST.json.

The generic calendar workbook was locally created for this project and verified
against the retained original. All 51 year worksheets (2000–2050) remain in the
unchanged file, SHA-256
`a0811fb64a2d28772a38a753f59bab5eb11f5c6ffff9244e0ebaf3bfa83fe6c3`.
It supplies an editable calendar structure, not official holidays or course
dates. The template's link is source-relative and self-contained; native GitBook
download behavior remains a separate acceptance test.

The initializer, focused tests, offline packager, metadata and concise instructions
were written for this candidate and revised for the integrated guide. They contain no previous generator, publisher,
machine ownership database or future-feature runtime. The positive App inventory
is fixed in scripts/course_init.py and APP-MANIFEST.json. Verification rejects
extra files or directories except a checkout's opaque root `.git` metadata,
which the initializer does not read or copy. The developer packager independently
reads exact Git objects to validate the clean App source pin, then exports only the fixed
positive inventories. Archives contain no Git metadata or historical source.
See [release packaging](docs/technical/release-packaging.md) for portable verification.

The owner approved MIT for this App template, tooling and project-created
workbook. The full terms are in LICENSE and are copied to each fresh workspace
outside its mapped course directory. New instructor/student content is outside
this source's ownership claim. The integrated [Docs user guide](docs/user/LICENSE.md)
and its diagrams/supporting documentation use CC BY 4.0, including attribution
and an integration change notice. The adapted `scripts/check_docs.py` retains
the original Docs source's CC BY 4.0 license, with creator and changes in its
header. Original App tooling and technical pages remain MIT. APP-MANIFEST
explicitly records both exceptions. Approval of these licenses does not assert that a release was published
or authorize a repository/Space visibility change.

Local integrity, path and link checks cannot certify publisher authenticity,
independent native reusable ownership, editor save/export fidelity, institutional
permissions or audience access. Those remain explicit release acceptance gates.
