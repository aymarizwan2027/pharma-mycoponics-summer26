# pharma-mycoponics-summer26
Data and analysis for characterization of exudate production in blue oyster mushroom mycoponics systems.

## Start here

A repository is the project folder. A **commit** is a saved change with a description. **main** is the primary version. The dataset from pull request #1 is now included in main; its original files and history are preserved.

| File or folder | Contents |
| --- | --- |
| `Chamber Conditions Daily` | Original CSV text of environmental measurements |
| `Chamber Tubes Daily` | Original CSV text of tube observations and photo references |
| `UUIDs and Date` | Original CSV text linking observation dates to record identifiers |
| [data/](data/) | Source-data organization and quality notes |
| [scripts/download_epicollect.ps1](scripts/download_epicollect.ps1) | Tested Windows downloader for the main form and both branches |

The original exports have no `.csv` filename extension, but their contents are CSV. Future exports should use dated filenames ending in `.csv`. Put source exports in `data/raw/`, cleaned tables in `data/processed/`, analysis scripts in `analysis/`, and figures in `figures/`. Create each folder when adding its first file.

## EpiCollect5 API links for collaborators

Project: [Mycoponics Porterfield](https://five.epicollect.net/project/mycoponics-porterfield). Form: **Mycopharmaceutical bioproduction**. Verified against the project API page on September 9, 2026. Mapping: `EC5_AUTO` (`map_index=0`).

- [Project endpoint](https://five.epicollect.net/api/export/project/mycoponics-porterfield): project and form definition.
- [Main-form entries](https://five.epicollect.net/api/export/entries/mycoponics-porterfield?form_ref=8a09dbeef84443df91d134da7b71b9e2_6a738dc33d46e): observation-date records.
- [Chamber conditions entries](https://five.epicollect.net/api/export/entries/mycoponics-porterfield?form_ref=8a09dbeef84443df91d134da7b71b9e2_6a738dc33d46e&branch_ref=8a09dbeef84443df91d134da7b71b9e2_6a738dc33d46e_6a7412262bf6f): environmental measurements.
- [Chamber entries](https://five.epicollect.net/api/export/entries/mycoponics-porterfield?form_ref=8a09dbeef84443df91d134da7b71b9e2_6a738dc33d46e&branch_ref=8a09dbeef84443df91d134da7b71b9e2_6a738dc33d46e_6a73c6a20258a): tube observations.

An endpoint is an address a program visits to retrieve data. Opening a link shows structured text called JSON. Use all three entries links: the main form does not contain all branch measurements. Each response may be only one page. The downloader retrieves every page. These are the Mycoponics identifiers, not the AIRI example.

## Download fresh CSV files on Windows

1. Choose the green **Code** button, then **Download ZIP**.
2. Extract the ZIP and open PowerShell in the extracted repository folder.
3. Run `& .\scripts\download_epicollect.ps1`.
4. Wait for **Saved snapshot**. Open the new dated folder inside `data/raw/epicollect/`. Its three CSV files contain dates, chamber conditions, and tube observations.

The script uses built-in Windows web tools, spaces requests 25 seconds apart, checks row counts and duplicate identifiers, and saves original JSON responses plus CSV tables. It creates a new folder on every run and only reads EpiCollect; it does not edit observations or replace previous exports. Run it when a fresh snapshot is needed; it is not scheduled.

Check that `manifest.json` says `complete: true` before using an export. If a request fails, its folder stays incomplete; resolve the error and rerun to create a new snapshot. If Windows blocks scripts, follow your computer's approved script-running policy.

All three tables were successfully downloaded without credentials on September 9, 2026: **55 date records, 216 chamber-condition records, and 828 tube records**. The original GitHub tube export also contains 828 records and 828 unique identifiers. Its quoted notes include line breaks, so counting text lines overstates the record count. Neither source has been overwritten.

Downloaded snapshots are kept local by default through `.gitignore`; review them before deliberately publishing. Photo references are retained, but image files are not downloaded. General Form and Forms 2–4 are outside this downloader's scope. If project access later becomes restricted, consult the [official EpiCollect5 API guide](https://developers.epicollect.net/); do not put passwords or tokens in this public repository.
