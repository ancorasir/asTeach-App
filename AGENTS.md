# asTeach App v0.1 source instructions

Read README.md and START-HERE.md before changing this generic product. Keep the
thirteen-section/twelve-resource course contract and positive manifest aligned.
Do not put real course content, private preparation, credentials or development
records in this source tree. New teaching content belongs to its instructor.

Use Python 3.9+ standard library for the optional initializer. It creates fresh
workspaces only; never extend it into an existing-course updater implicitly.
Preserve unknown files and all authored inputs. Use apply_patch for source edits.
Regenerate the content manifest after authorized changes, then run the full suite
shown in START-HERE.md and verify the complete distribution inventory.

This is release-candidate source. Its own commit identity belongs only in the
external RELEASE-MANIFEST.json; source manifests never embed their future commit.
Use scripts/package_release.py for reviewed offline packaging from two independent,
clean Git roots at exact App/Docs commits. See docs/release-packaging.md.
Native acceptance and publication remain pending; packaging does not perform them.
Keep GitBook import, reusable ownership, editor fidelity and intended reader
access as separate acceptance checks. No tool or instruction here grants remote
creation, mapping, publishing, access changes or permission to send user content.
