# Existing research code and the US-01 application story

Reviewed source: `Codes and Database.zip`, supplied October 15, 2026. The archive contains 21 entries, including the note referring to 20 project files. The original archive is retained byte-for-byte under `reference-originals` in the delivery package, outside the files intended for this story's GitHub upload.

## Database

`engagetrace_db.py` and `schema.sql` define the original SQLite database. `engagetrace_db_pg.py` and `supabase_schema.sql` are an alternative Postgres implementation. No `engagetrace.db` or raw OULAD CSVs are in the supplied archive, so the claimed full database size and its contents have not been verified. Saved JSON course exports are present; they cannot reconstruct the original source-file checksums or all registration information.

US-01 retains SQLite as the selected local database. Its import command creates a persistent database automatically and adds versioned source-staging tables. This is a deliberate first step toward the normalized application schema, not a complete replacement for all research tables. A compatibility test initializes the uploaded legacy schema, inserts a course/student/activity row, imports the synthetic CSVs into that same database, and confirms the old activity and detection tables remain intact. A failed second import also preserves the old activity. The uploaded SQL is included unchanged as a test fixture. This test verifies schema coexistence, not end-to-end detector integration or migration of the missing 506 MB database.

Use a separate path such as `data/engagetrace-import.sqlite3` for application development. Back up any existing research database before eventually migrating it. No database binary or full OULAD dataset is included in the GitHub upload files. The example CSVs rebuild a tiny test database with the documented command.

The legacy ingest method aggregates to one-based weeks and adds clicks on conflict. Reimporting the same CSV through that method would add the same totals again. The requirements use zero-based `floor(date / 7)` weeks for on/after-start events. US-01 therefore stages source dates unchanged and prevents duplicate versions; US-02 must explicitly resolve week numbering, numeric validation, coverage, enrollment eligibility and the mapping into the application domain tables. No existing weekly totals are silently rewritten.

## Dashboard

Keep `engagetrace_dashboard.html` and `bundle.js` together when opening the supplied standalone dashboard. The JSX source has synthetic data, course-JSON loading and optional Supabase reads. There is no direct local SQLite connection in the HTML. The standalone file does not acquire a live connection merely because a database exists on disk. A Python API and a shared detector implementation remain later application work. The JSX and bundle were preserved, not rebuilt or certified equivalent in this story.

## Research reconciliation deferred

The supplied SQLite detector uses raw relative declines and leave-one-out MAD context scores. The supplied evaluation uses lagged log1p declines and cohort percentile ranks. The dashboard contains its own JavaScript detector; its individual-only baseline uses an unlagged window, whereas controlled_eval.py applies a lag to that baseline. Default log thresholds also differ. These are material implementation differences, not evidence that saved results are incorrect; outputs must be reconciled against exact configurations before publication.

This assignment does not change detector equations, saved JSON results, dashboard files, or manuscript claims. Later ICICIP work must select and version a single protocol, reproduce saved outputs, align Python/database/UI computation and perform held-out validation. Import acceptance tests do not establish research validity.

## US-01 acceptance

The first story is still issue #1: importing the three required OULAD CSV files creates a version and summary; missing required columns stop import clearly. Thirteen automated tests now pass, including coexistence with the uploaded SQLite schema. Validation uses synthetic inputs because the raw OULAD CSVs were not supplied.
