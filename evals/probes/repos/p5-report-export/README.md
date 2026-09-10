# reportsvc (probe fixture)

A small reporting service. Customers have reports; reports can be
exported as CSV today. The task (see TASK.md) adds PDF export behind an
async job.

## Layout

- `app/models.py` — `Report`, `Customer` data models.
- `app/queries.py` — the report query functions (the ONLY place report
  rows are fetched — everything else must go through here).
- `app/services/export.py` — the existing CSV export.
- `app/api.py` — endpoint handler functions.
- `tests/test_export.py` — the suite that must stay green.

## Platform notes

- Python 3.11, stdlib only. No job/queue library is available — if async
  work is needed, the design must roll its own (in-process is acceptable
  at this scale).
- PDF generation: stdlib cannot render PDFs; the fixture assumes a
  `pdflib_shim.py` module will be vendored (it is a 40-line wrapper the
  platform team provides). The plan should treat "vendor the shim" as a
  real task, not a magic import.
