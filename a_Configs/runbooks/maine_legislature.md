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

### As-of date

- `as_of` is the "Updated" date on the cover page (page 1) of the newest PDF you added or revised, e.g. "Updated May 8, 2026" is `2026-05-08`.

## Configuration/Testing

Goal: get the new or revised budget PDF through preprocessing with every validation check passing for its biennium, fixing failures by editing config files only.

The ingest script has already run preprocessing and validation once for this biennium; you're here because something failed. Your prompt has the results and the exact commands. Run all commands from the repository root.

### 1. Update the config for the biennium

In `a_Configs/config.py`:
- `ME_BUDGET_END_PAGES`: needs an entry for the biennium. The value is one past the last summary page: the summary ("Table of Contents") pages start at page index 1, and the last one ends with the grand totals (`GRAND TOTALS - ALL DEPARTMENTS`) and has a footer like `Table of Contents - Page 8 of 8`. For example, summary pages 1-8 means `9`. For a new biennium, add the entry. For a revised PDF, keep the existing value unless validation says it's wrong.
- `ME_POSITION_YEARS`: add the biennium if it's missing.

Validation fails `configured (…)` when either entry is missing.

### 2. Run preprocessing

Use the preprocessing command from your prompt. It processes budgets and positions for this biennium only (`--year`) and takes under a minute. With `--quiet` it prints only warnings and errors; any `WARNING` or `ERROR` line (such as `No data extracted`) is a failure. Full logs go to `logs/preprocessing.log`.

### 3. Run validation

Use the validation command from your prompt. With `--failures-only` it prints each failed check (✗) with its problems, then a summary, and exits 1 if anything failed. Only check the biennium you're working on. Known failures elsewhere, such as the scanned FY 2019 revenue PDF, are out of scope.

### 4. Fix failures

Fix each failure as below, then repeat steps 2 and 3. Stop after three rounds of fixes that don't get everything passing, and report what's still failing.

| Failing check | What it means | Fix |
|---|---|---|
| `configured (ME_BUDGET_END_PAGES)` or `configured (ME_POSITION_YEARS)` | The biennium is missing from that setting, so the app won't load it. | Add it as in step 1. |
| `processed_file_exists` | Preprocessing didn't produce a file for this biennium. | Check the preprocessing output and log for the error. If the PDF couldn't be read or has no summary pages, the file is probably wrong: send it back to the sourcing agent (see step 6). |
| `staleness` | The processed file doesn't match the PDF. | Re-run step 2. If it still fails, report it; that's a code problem. |
| `summary_pages` | `ME_BUDGET_END_PAGES` doesn't cover exactly the summary pages. | Set it to the value the message gives ("…so it should be N"). |
| `mapping (As Reported)` | A department in the budget has no row in `a_Configs/department_mapping.csv` (or has more than one). | Add one row: `State` = `Maine`, `As Reported` = the name exactly as in the message, `Standardized` = an existing category (see below), `Shortened Name` = a short display name in the same style as existing rows, `Positions As Reported` = the department's name in the positions section (from the positions check, or leave blank if it has no positions yet). If a department was renamed, add a row for the new name; don't change the old row, since older budgets still use it. |
| `mapping (Positions As Reported)` | A department in the positions section doesn't match any `Positions As Reported` value. | Find the department's row in `department_mapping.csv`. Its `Positions As Reported` holds the current name: if that value is still used by older bienniums, first move it to `a_Configs/positions_backhistory.csv` (columns `State`, `Positions As Reported`, `As Reported`, `Notes`, with a note saying which bienniums use it). Then set the mapping row to the new name. If the department has no mapping row at all, fix the `As Reported` mapping first. |
| `mapping (As Reported)` on `positions … backhistory` | A row in `positions_backhistory.csv` points at a department that isn't in `department_mapping.csv`. | Correct the backhistory row's `As Reported` to match the mapping exactly. |
| `funding_source_totals` where one fund shows only in the departments and another only in the grand totals, with identical amounts | The PDF names one fund two ways. | Add `{grand totals name: department name}` to `ME_FUNDING_SOURCE_ALIASES` in `a_Configs/config.py`. |
| `department_totals`, `grand_total`, or any other `funding_source_totals` failure | The parsed numbers don't add up, which usually means a parsing problem. | First check that `summary_pages` passes, since missing pages cause these. If it does, don't try to fix it: report the failing lines. |

Choosing a `Standardized` category: use one that already appears in the `Standardized` column for Maine, picking the one used by similar departments (for example, other commissions under the same parent department). Never invent a new category. If no existing category clearly fits, leave the department unmapped and report it for a human to decide.

### 5. Finish

When every check for the biennium passes, report what you changed in each file, and anything a human should review, such as a new department mapping or alias. The ingest script sets `last_updated` itself.

### 6. Send it back to the sourcing agent

If the problem is the PDF itself (for example, it isn't the full Appropriations and Allocations document, it has no summary pages, or it's for the wrong biennium), don't change the config. Report it as feedback for the sourcing agent: what's wrong with the file and what to pull instead.

### Rules

- Only edit these files: `a_Configs/config.py` (`ME_BUDGET_END_PAGES`, `ME_POSITION_YEARS`, `ME_FUNDING_SOURCE_ALIASES`), `a_Configs/department_mapping.csv`, and `a_Configs/positions_backhistory.csv`. Preprocessing writes `preprocessed_data/` and `logs/`; don't edit those by hand.
- Never edit code, including `scripts/validate_data.py`, and never change a check so it passes. If the only fix is a code change, report it.
- Keep the mapping files' existing format: column order, quoting, and line endings.
