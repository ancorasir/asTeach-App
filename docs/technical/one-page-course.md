# One-Page course contract — App v0.1

The [template Home](../../templates/one-page/README.md) is a static, directly editable
course with one navigation entry. It preserves the literal title
`[CourseCode] CourseName` and separate plain `Year Season` description. Home has
no explicit layout override and uses GitBook's Product Docs/default-width
presentation. Update Home and SUMMARY titles together.

The fixed section order is Course Description; Teaching Goals; Learning Outcomes;
Content Summary; Assumed Knowledge; Co-Requisite Courses; Course Instructor &
Teaching Team; Grading Policy; Academic Integrity; University Calendar;
Recommended Textbook(s); Teaching Schedule; Important Deadlines.

Each of the thirteen sections includes its own resource under
`.gitbook/includes/`. Learning Outcomes contains replaceable outcome-writing
guidance and a bullet placeholder. Co-Requisite Courses has its own resource
with concurrent-course guidance and a bullet placeholder. Keep all thirteen
resources as includes on the private Teacher Home; flattening that editing source
would change the contract. Fresh Teacher Home uses Product Docs at default width.

## Term and Student copies

Each `Year Season` term snapshot is ordinary detached content, with no reusable
includes. Preserve the accepted title, description, wording, list structure,
schedule and links. Historical term pages use Docs presentation at default width.
The Student page also uses Docs/default width and is independently owned: no
Teacher reusable or Teacher asset references. This is a manual content workflow;
the initial inventory remains seventeen mapped files and twenty workspace files.
The layout correction removes only Home's prior layout override; its description,
full body and all other course payload bytes are retained. Existing courses need
a separately reviewed layout change.
No term generator, existing-course updater or Teacher-to-Student publisher is
included.

Omit an entire section from a term only when the instructor confirms its complete
answer is exactly `None`. Blank, unknown, ambiguous or partly answered sections
do not qualify. Keep the Teacher heading, resource and supplied answer intact.
Never supply missing policy or course facts; a late-submission rule requires the
instructor's supplied wording.

Use ordinary links to annual top-level folders in a separate materials repository.
GitHub blob/PDF file-view and download links are distinct from inline images;
private GitHub image access cannot serve anonymous readers. An explicitly
approved Library calendar exception uses an image owned by the target Space,
meaningful alt text, rights/attribution checks and verified full-size rendering.
A Student copy needs its own asset, even when the pixels match the Teacher image.
Materials access is checked separately from page publication.

Before a transfer or update, reconcile the full saved export, source Library
edits, open drafts/comments and current repository. A Git diff alone cannot
establish native resource state. After saving, compare the complete exported
inventory and body with the accepted source, inspect native and published views
separately, and test existing routes as well as new ones. An unchanged filename
does not prove that its native URL remains unchanged. Preserve source and stop
for reconciliation on unexplained drift; do not reimport or overwrite a course.

## Supplied template and acceptance

The supplied paragraphs, bullets, people fields, book patterns, module headings,
class entries and deadlines are replacement guidance. They supply no course facts.
Schedule titles and dates are edited manually. There are no generated classes,
per-class pages, automated deadlines or required module jump links. Navigate to
the top-level Teaching Schedule section and scroll to modules; native deep links
inside reusable includes are outside this contract.

The calendar block's `../assets/calendar-2000-2050.xlsx` link is relative to its
source include in `.gitbook/includes/`, resolving to `.gitbook/assets/` inside the
same mapped course. The original workbook bytes are retained. It is a generic
editable calendar, not an official university schedule. Use a local customized
copy and replace guidance with your approved screenshots and alternative text.

Initialization creates seventeen course files plus three workspace files outside
the mapping. Map only `course/`; configuration inside it uses `root: ./`,
`readme: README.md`, `summary: SUMMARY.md`. No private preparation, generator,
ownership state or future feature ships in the mapped course.

Static tests verify the template and source-relative references. New native
GitBook import, all thirteen resources' independent ownership, rich-editor
editing, saved/exported layout and actual workbook downloads still need acceptance
against the exact released files. ZIP import and Space duplication are not
accepted substitutes for this contract. Setup does not choose reader permissions.

See [START-HERE](../../START-HERE.md) and the included
[asTeach Docs v0.1.1 user guide](../user/README.md).
