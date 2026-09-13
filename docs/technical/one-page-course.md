# One-Page course contract — App v0.1

The [template Home](../../templates/one-page/README.md) is a static, directly editable
course with one navigation entry. It preserves the literal title
`[CourseCode] CourseName`, separate plain `Year Season` description and wide
layout settings. Update Home and SUMMARY titles together.

The fixed section order is Course Description; Teaching Goals; Learning Outcomes;
Content Summary; Assumed Knowledge; Co-Requisite Courses; Course Instructor &
Teaching Team; Grading Policy; Academic Integrity; University Calendar;
Recommended Textbook(s); Teaching Schedule; Important Deadlines.

Each section except Co-Requisite Courses includes its own resource under
`.gitbook/includes/`. Learning Outcomes contains replaceable outcome-writing
guidance and a bullet placeholder. Co-Requisite Courses is ordinary Home content
with concurrent-course guidance and a bullet placeholder. Keep all twelve resources as includes; a flattened
Markdown page would change the editing contract.

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

Initialization creates sixteen course files plus three workspace files outside
the mapping. Map only `course/`; configuration inside it uses `root: ./`,
`readme: README.md`, `summary: SUMMARY.md`. No private preparation, generator,
ownership state or future feature ships in the mapped course.

Static tests verify the template and source-relative references. New native
GitBook import, all twelve resources' independent ownership, rich-editor
editing, saved/exported layout and actual workbook downloads still need acceptance
against the exact released files. ZIP import and Space duplication are not
accepted substitutes for this contract. Setup does not choose reader permissions.

See [START-HERE](../../START-HERE.md) and the included
[asTeach Docs v0.1.1 user guide](../user/README.md).
