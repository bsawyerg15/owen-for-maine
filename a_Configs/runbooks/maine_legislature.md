# Runbook: Maine State Budget (Maine Legislature)

Source key: `maine_legislature` (see `a_Configs/sources_config.py`)

## Sourcing

### Where to pull the data from

- Page: https://legislature.maine.gov/ofpr/total-state-budget-information/9304
  (Maine Legislature, Office of Fiscal and Program Review: Total State Budget Information)
- Maine budgets are biennial, so there is one budget PDF per two-year period (e.g. `2026-2027`).
- New data is available when the page lists a PDF for a biennium that isn't already in `z_Data/ME/`.

### Storage Instructions

- What to store: store the full raw PDF file
- Directory: `z_Data/ME/` (`Config.DATA_DIR_ME` in `a_Configs/config.py`)
- Format: `<YYYY>-<YYYY> ME State Budget.pdf`
- Example: `2026-2027 ME State Budget.pdf`
- The year range is the biennium, written as the first and second year joined by a hyphen.
- The name must match exactly. `b_App/data_ingestion.py` and `scripts/preprocess_pdfs.py` look up files by the pattern `*ME State Budget.pdf` and read the year range from the start of the file name.

## Configuration/Testing

TODO
