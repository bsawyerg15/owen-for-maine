# Runbook: Maine State Budget (Maine Legislature)

Source key: `maine_legislature` (see `a_Configs/sources_config.py`)

## Sourcing

### Where to pull the data from

- Page: https://legislature.maine.gov/ofpr/total-state-budget-information/9304
  (Maine Legislature, Office of Fiscal and Program Review: Total State Budget Information)
- Maine budgets are biennial, so there is one budget PDF per two-year period (e.g. `2026-2027`).
- New data is available when the page lists a PDF for a biennium that isn't already in `z_Data/ME/`.

### Checking for revisions

- The Legislature re-publishes the budget PDF for the current biennium after each legislative session, under the same biennium. Older bienniums are final and don't need checking.
- Check the latest biennium already in `z_Data/ME/` for a revision: download the page's PDF for that biennium to a temp location and compare its checksum with the stored file.
- If the checksums differ, compare the cover pages (page 1) of both PDFs. Each says which session it runs through (e.g. "Through the 132nd Legislature, 2nd Regular Session") and when it was updated (e.g. "Updated May 8, 2026").
  - Read the cover pages with `pdfplumber`, which is installed: `python3 -I -c "import sys, pdfplumber; print(pdfplumber.open(sys.argv[1]).pages[0].extract_text())" <file.pdf>`. Don't look for other PDF tools.
  - If the download is newer, replace the stored file with it, keeping the same file name. This is revised data.
  - If the download is older or has the same updated date, escalate.
- If the checksums match, there is no revision.

### Storage Instructions

- What to store: store the full raw PDF file
- Directory: `z_Data/ME/` (`Config.DATA_DIR_ME` in `a_Configs/config.py`)
- Format: `<YYYY>-<YYYY> ME State Budget.pdf`
- Example: `2026-2027 ME State Budget.pdf`
- The year range is the biennium, written as the first and second year joined by a hyphen.
- The name must match exactly. `b_App/data_ingestion.py` and `scripts/preprocess_pdfs.py` look up files by the pattern `*ME State Budget.pdf` and read the year range from the start of the file name.

## Configuration/Testing

TODO
