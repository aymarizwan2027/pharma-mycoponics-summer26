# Research data

The original exports remain at the repository root with their original names and contents. They contain CSV text, even though their filenames do not end in `.csv`.

- `Chamber Conditions Daily`: environmental measurements.
- `Chamber Tubes Daily`: tube observations and photo references.
- `UUIDs and Date`: observation dates and parent record identifiers.

For future source exports, use `data/raw/` and a dated filename ending in `.csv`. Save cleaned or joined tables in `data/processed/`, documenting each transformation. The API downloader creates dated folders inside `data/raw/epicollect/`; these are kept local by default. A successful snapshot includes three CSV tables, original JSON responses, the project definition, and a manifest with `complete: true`.

## Connecting the tables

Join branch `ec5_branch_owner_uuid` to the dates table's `ec5_uuid`. Use `1_Date` for the observation date, not `created_at` or `uploaded_at`. The original dates use day/month/year. Retain tube identifiers such as A2 and all UUIDs when linking to other experiments. A confirmed sample-to-tube mapping is still needed for RNA-seq or mass-spectrometry integration. Photo references are not the image files themselves.

## Review before analysis

- Temperatures include values around 65–83 and others around 20–30. Confirm units against original records before conversion.
- One chamber-condition row has humidity 642 and CO2 50. Check the original observation for a possible transcription or column swap.
- Missing measurements and sensor-failure notes are not zeros.
- The September 9, 2026 API test retrieved 55 date records, 216 chamber-condition records, and 828 tube records. The original GitHub tube export has 830 data rows. Investigate the difference before combining the snapshots. Neither source has been overwritten.
