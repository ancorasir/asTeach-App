# asTeach App v0.1

One-Page GitBook Course Template by SONG Chaoyang ([songcy@ieee.org](mailto:songcy@ieee.org)) @ Design and Learning Research Group ([https://AncoraSIR.com](https://AncoraSIR.com)).

Create one course Home and edit its reusable sections directly in GitBook.
The template supplies visible replacement guidance; the instructor supplies the
course content, dates, people, grading and policies. Ordinary editing requires
no agent, generator or Python.

This release-candidate source includes asTeach Docs v0.1.1 in `docs/user/`. A packaged cohort's
external RELEASE-MANIFEST.json records the exact integrated App source commit and
archive hash. Source manifests record content integrity without embedding their
own future commit. Hosted import, resource ownership, editor round trip and
publication acceptance remain pending. No published release or tag is claimed.

Start with [START-HERE.md](START-HERE.md). The
[course contract](docs/technical/one-page-course.md) describes thirteen sections and twelve
reusable resources. [Optional initialization](docs/technical/initializer.md) creates a
fresh local workspace and preserves every existing course.

The mapped `course/` folder contains one Home, its includes and a generic calendar
workbook. Repository instructions and the license stay outside that mapping.
Private preparation and other course material belong in separately managed
locations chosen by the instructor.

Original App tooling, technical documentation, blank template and included generic workbook use the [MIT license](LICENSE).
The [user guide and its diagrams](docs/user/README.md) use [CC BY 4.0](docs/user/LICENSE.md);
the adapted guide checker also retains CC BY 4.0. These exceptions are recorded
explicitly in the source manifest.
The license does not claim ownership of instructor or student contributions.
See [provenance](PROVENANCE.md), [changes](CHANGELOG.md) and the
[file manifest](APP-MANIFEST.json). Checksums establish integrity, not publisher
authenticity; compare the archive checksum with the publisher's trusted release
record before running downloaded code.

The version-matched asTeach Docs v0.1.1 guide is included in the single App archive.
The App's GitBook mapping remains `templates/one-page/`; guide hosting is a
separate choice and no user-guide pages become course Home content.
Multi-Page courses, automatic publishing, team repository setup
and plugins are outside v0.1.

Developers can [package exact committed source](docs/technical/release-packaging.md) with
the offline builder. Ordinary course creation does not need Git or that builder.
