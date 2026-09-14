# Calendar and Files

Docs v0.1.1 · for App v0.1 · release candidate

The generic workbook is in your course workspace at
`course/.gitbook/assets/calendar-2000-2050.xlsx`. Open it locally from the
extracted files. It has year sheets for 2000–2050, blank Week # cells, continuous
week rows and neutral month bands. It supplies no university holidays,
teaching weeks or course dates.

## Prepare the course calendar

1. Save a working copy outside the mapped course directory.
2. Choose the year sheet and enter your own week numbers and verified
   institutional/course dates.
3. Make readable calendar images from the relevant area, using only material
   you are authorized to share. Check that no other windows or personal details
   appear in a capture.
4. In the University Calendar reusable block, remove the setup workbook link
   and guidance from the finished course text. Insert your calendar image(s)
   into that existing block.
5. Add alt text identifying the calendar's term and purpose, and a nearby text
   equivalent for dates and events that readers need. Keep important dates
   available as text; alt text alone is not a full calendar transcription.
6. Save, reopen and inspect the entire uncropped image at ordinary desktop and
   narrow-page width. Open the full-size image and verify its detail and owner;
   inspect native and published rendering separately.

![Schematic: customize the generic workbook locally, create an authorized readable calendar image, then add the image, alt text and equivalent dates as text to the calendar block.](assets/05-calendar-alt.svg)

Figure 5. Calendar preparation and accessibility workflow; schematic, not an
image of an institutional calendar or GitBook controls.

The included workbook link is a local source-relative link. A successful local
open does not prove a hosted download. Native workbook downloads and the new
image editing round trip remain pending for this candidate. Do not rely on the
starter workbook link as a student delivery method.

## Choose how to deliver other files

| Method | What to verify |
| --- | --- |
| GitBook native file block | GitBook stores an uploaded copy. Test Open and Download from the intended reader's view. |
| Ordinary external file link | The reader visits that host. Test authorization, filename and completed download. |
| Separate materials repository | Use ordinary links to annual top-level folders such as `year-season/`; access applies to that repository. |

GitBook documents [uploading and inserting files](https://gitbook.com/docs/create-content/blocks/insert-files).
Uploading a file and adding a link to an existing file are different actions.

A private GitHub link requires an authorized account. Making course materials
accessible does not require making course source public: separate materials
storage is an option you choose. Review the rights and metadata of each file,
then test the actual intended audience. This candidate does not create storage,
upload materials or change their access.

## Separate download links from inline images

A GitHub blob/PDF link opens a file-view page; verify the completed download
separately. It is not an inline image URL. Private GitHub images cannot render
for anonymous readers without authorized access. Renaming a file extension or
linking its file-view page does not change its encoding or access.

When the instructor explicitly approves a Library calendar exception, use an
image owned by the target GitBook Space alongside the ordinary materials link.
Check the actual image format, sharing rights, attribution, useful alt text and
full-size uncropped display. For a Student page, retain or insert an independently
Student-owned image; do not bind it to the Teacher's Library. Preserve unrelated
Library entries and compare any retained calendar with the accepted source.

Keep the intended materials links in their annual folders. This workflow does
not redesign delivery around release assets or change repository visibility.
A published page does not make its private file links public. Report an editor
failure and a successful published image as separate results; neither proves
the other view works.
