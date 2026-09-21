# inputs/

What the build needs beside this repository:

* `fonts/` — Montserrat 400/600/800 (OFL), embedded into the single-file report.
* `yac images for report/` — the three Brain Break character images (Sport Wales / YAC assets).
* `18117 Chwaraeon Cymru 2026 School Sport Survey - School Reports.docx` — the translator's document
  of 15 Sep 2026 (also `config/SSS2026_Welsh_translation_document_15Sep2026.docx`).
* `School Reports Accessibility Feedback.docx` — the accessibility feedback implemented in V4.13.

**Deliberately not in the repository:** the pupil-level response export
(`SSS2026_YPD_export_headers_cleaned_copy.xlsx`, sha256 e457bc8e…) and any school response data.
The build takes the export's path as its first argument (`pipeline.staged_build states <export> …`);
it lives on the owner's machine (Downloads) and in the rebuild kits shipped there, never here.
The cover media (`config/cover_media/`) is already in the repository.
