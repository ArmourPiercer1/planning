# Task: monthly PDF export of customer reports

Add a monthly PDF export of a customer's reports.

Requirements:

1. Reuse the existing report queries in `app/queries.py` — do not
   duplicate query logic anywhere else in the service.
2. New endpoint `POST /reports/{id}/export-pdf` — enqueues the export and
   returns immediately.
3. Async job: exports run after the endpoint returns; the client polls
   `GET /jobs/{id}` until the job is done, then downloads the PDF via
   `GET /jobs/{id}/download`. The service has no job infrastructure
   today — design one (in-process is fine at this scale).
4. PDF content: one page per report, using the vendored `pdflib_shim`
   (see README, Platform notes).
5. Labels in the PDF must be available in English and German (i18n),
   selected by a `lang` field on the request (default `en`).

Out of scope (do not plan for these):

- Email delivery of the exported PDF.
- Report editing / creation (only export of existing reports).
- Historical archive or retention policy for old exports.

Existing behavior and tests must stay green.
