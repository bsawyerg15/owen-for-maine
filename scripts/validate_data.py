#!/usr/bin/env python3
"""
Validation for the pre-processed data

Checks that each pre-processed file is up to date with its source PDF and that the parsed
values are internally consistent (mappings exist, line items add up to the published totals).

Usage:
    python scripts/validate_data.py                         # Validate everything
    python scripts/validate_data.py --budget                # Maine budgets only
    python scripts/validate_data.py --revenue               # Revenue only
    python scripts/validate_data.py --positions             # Positions only
    python scripts/validate_data.py --budget --year 2026-2027  # One period
"""

import sys
import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
import pdfplumber

# Add project root to path
sys.path.append('.')

from a_Configs.config import Config
from b_App.me_budget_parser import parse_me_headline_table, read_me_budget_summary
from preprocess_pdfs import load_me_general_fund_source_table, revenue_table_to_numeric

logger = logging.getLogger(__name__)

TOLERANCE = 1.0  # dollars
MAX_PROBLEMS_SHOWN = 10

BUDGET_PDF_DIR = Path(Config.DATA_DIR_ME)
REVENUE_PDF_DIR = Path(Config.DATA_DIR_GEN_FUND_SOURCES)
BUDGET_OUTPUT_DIR = Path("preprocessed_data/budgets")
REVENUE_OUTPUT_DIR = Path("preprocessed_data/revenue")
POSITIONS_OUTPUT_DIR = Path("preprocessed_data/positions")

GRAND_TOTALS = 'GRAND TOTALS - ALL DEPARTMENTS'
DEPARTMENT_TOTAL = 'DEPARTMENT TOTAL'
REVENUE_AMOUNT_COLUMNS =['Month Actual', 'Month Budget', 'Month Variance',
                          'FYTD Actual', 'FYTD Budget', 'FYTD Variance', 'Total Budgeted FY']


@dataclass
class CheckResult:
    check: str
    target: str
    passed: bool
    problems: list[str] = field(default_factory=list)


def _result(check, target, problems):
    return CheckResult(check, target, not problems, problems)


def _fmt(value):
    return f"{value:,.0f}"


# ---------------------------------------------------------------------------
# Shared checks
# ---------------------------------------------------------------------------

def check_processed_file_exists(processed_path, target):
    """The source PDF has a pre-processed file."""
    problems = [] if processed_path.exists() else [f"No pre-processed file at {processed_path}; run preprocessing"]
    return _result('processed_file_exists', target, problems)


def check_configured(period, setting_name, setting, target):
    """The period is listed in a config setting the app reads its periods from."""
    problems = [] if period in setting else [f"{period} is missing from Config.{setting_name} in a_Configs/config.py, so the app won't load it"]
    return _result(f'configured ({setting_name})', target, problems)


def check_staleness(processed_df, source_df, target):
    """The pre-processed file matches a fresh parse of the source PDF."""
    problems = []
    if not processed_df.index.equals(source_df.index):
        missing = source_df.index.difference(processed_df.index)
        extra = processed_df.index.difference(source_df.index)
        problems.append(f"Rows differ: {len(missing)} in the PDF but not the processed file, {len(extra)} the other way")
        problems += [f"Only in PDF: {row}" for row in list(missing)[:MAX_PROBLEMS_SHOWN]]
        problems += [f"Only in processed file: {row}" for row in list(extra)[:MAX_PROBLEMS_SHOWN]]
        return _result('staleness', target, problems)
    if list(processed_df.columns) != list(source_df.columns):
        return _result('staleness', target, [f"Columns differ: {list(processed_df.columns)} vs {list(source_df.columns)}"])

    numeric_columns = processed_df.select_dtypes('number').columns
    processed_values = processed_df[numeric_columns].fillna(0).to_numpy()
    source_values = source_df[numeric_columns].fillna(0).to_numpy()
    for i, j in zip(*((abs(processed_values - source_values) > TOLERANCE).nonzero())):
        problems.append(f"{processed_df.index[i]} {numeric_columns[j]}: processed {_fmt(processed_values[i, j])}, PDF {_fmt(source_values[i, j])}")
    if len(problems) > MAX_PROBLEMS_SHOWN:
        problems = problems[:MAX_PROBLEMS_SHOWN] + [f"...and {len(problems) - MAX_PROBLEMS_SHOWN} more"]
    return _result('staleness', target, problems)


def check_mapping(names, mapping_df, state, column, target, maps_to='Standardized'):
    """Every name has exactly one row for the state in the mapping, with `maps_to` filled in."""
    state_rows = mapping_df[mapping_df['State'] == state]
    problems = []
    for name in sorted(set(names)):
        rows = state_rows[state_rows[column] == name]
        if rows.empty:
            problems.append(f"No mapping for '{name}' (column '{column}')")
        elif len(rows) > 1:
            problems.append(f"'{name}' has {len(rows)} mapping rows (column '{column}'); expected one")
        elif pd.isna(rows[maps_to].iloc[0]):
            problems.append(f"'{name}' has a mapping row with no '{maps_to}' value (column '{column}')")
    return _result(f'mapping ({column})', target, problems)


# ---------------------------------------------------------------------------
# Budget checks
# ---------------------------------------------------------------------------

def _summary_page_indexes(pdf, max_pages=20):
    """Pages whose footer marks them as part of the Table of Contents summary."""
    indexes = []
    for i, page in enumerate(pdf.pages[:max_pages]):
        lines = (page.extract_text() or '').strip().split('\n')
        if 'Table of Contents' in lines[-1]:
            indexes.append(i)
    return indexes


def check_summary_pages(pdf, end_page, target):
    """ME_BUDGET_END_PAGES reads exactly the summary pages, ending with the grand totals."""
    problems = []
    summary = _summary_page_indexes(pdf)
    if not summary:
        return _result('summary_pages', target, ["No 'Table of Contents' summary pages found"])
    expected_end = summary[-1] + 1
    if summary != list(range(1, expected_end)):
        problems.append(f"Summary pages are {summary}; expected them to run continuously from page 1")
    if end_page != expected_end:
        problems.append(f"ME_BUDGET_END_PAGES is {end_page} but the summary ends at page {summary[-1]}, so it should be {expected_end}")
    if GRAND_TOTALS not in (pdf.pages[summary[-1]].extract_text() or ''):
        problems.append(f"Last summary page ({summary[-1]}) doesn't contain '{GRAND_TOTALS}'")
    return _result('summary_pages', target, problems)


def _department_rows(budget_df):
    return budget_df.drop(index=GRAND_TOTALS, level='Department', errors='ignore')


def check_department_totals(budget_df, target):
    """Each department's funding sources add up to its DEPARTMENT TOTAL."""
    problems = []
    for dept, rows in _department_rows(budget_df).groupby(level='Department'):
        funds = rows.index.get_level_values('Funding Source')
        if DEPARTMENT_TOTAL not in funds:
            problems.append(f"{dept}: no {DEPARTMENT_TOTAL} row")
            continue
        total = rows[funds == DEPARTMENT_TOTAL].sum()
        line_items = rows[funds != DEPARTMENT_TOTAL].sum()
        for year in budget_df.columns:
            if abs(line_items[year] - total[year]) > TOLERANCE:
                problems.append(f"{dept} {year}: funding sources sum to {_fmt(line_items[year])}, {DEPARTMENT_TOTAL} is {_fmt(total[year])}")
    return _result('department_totals', target, problems)


def check_funding_source_totals(budget_df, target):
    """Each funding source, summed across departments, matches its row in the grand totals section."""
    if GRAND_TOTALS not in budget_df.index.get_level_values('Department'):
        return _result('funding_source_totals', target, [f"No '{GRAND_TOTALS}' section was parsed"])
    dept_rows = _department_rows(budget_df)
    dept_funds = dept_rows[dept_rows.index.get_level_values('Funding Source') != DEPARTMENT_TOTAL]
    by_fund = dept_funds.groupby(level='Funding Source').sum()

    grand = budget_df.xs(GRAND_TOTALS, level='Department')
    grand_funds = grand[~grand.index.str.startswith(('SUBTOTAL', 'GRAND TOTALS'))]
    grand_funds = grand_funds.rename(index=Config.ME_FUNDING_SOURCE_ALIASES).groupby(level=0).sum()

    problems = []
    for fund in sorted(set(by_fund.index) | set(grand_funds.index)):
        for year in budget_df.columns:
            dept_sum = by_fund[year].get(fund, 0.0)
            published = grand_funds[year].get(fund, 0.0)
            if abs(dept_sum - published) > TOLERANCE:
                problems.append(f"{fund} {year}: departments sum to {_fmt(dept_sum)}, grand totals show {_fmt(published)}")
    return _result('funding_source_totals', target, problems)


def check_grand_total(budget_df, target):
    """Department totals and the grand totals subtotals both add up to the grand total."""
    try:
        grand_total = budget_df.loc[(GRAND_TOTALS, GRAND_TOTALS)]
    except KeyError:
        return _result('grand_total', target, [f"No '{GRAND_TOTALS}' row was parsed"])
    if isinstance(grand_total, pd.DataFrame):
        grand_total = grand_total.iloc[-1]

    dept_rows = _department_rows(budget_df)
    dept_sum = dept_rows[dept_rows.index.get_level_values('Funding Source') == DEPARTMENT_TOTAL].sum()
    grand = budget_df.xs(GRAND_TOTALS, level='Department')
    subtotal_sum = grand[grand.index.str.startswith('SUBTOTAL')].sum()

    problems = []
    for year in budget_df.columns:
        if abs(dept_sum[year] - grand_total[year]) > TOLERANCE:
            problems.append(f"{year}: {DEPARTMENT_TOTAL} rows sum to {_fmt(dept_sum[year])}, grand total is {_fmt(grand_total[year])}")
        if abs(subtotal_sum[year] - grand_total[year]) > TOLERANCE:
            problems.append(f"{year}: SUBTOTAL rows sum to {_fmt(subtotal_sum[year])}, grand total is {_fmt(grand_total[year])}")
    return _result('grand_total', target, problems)


# ---------------------------------------------------------------------------
# Revenue checks
# ---------------------------------------------------------------------------

def check_revenue_totals(revenue_df, target):
    """The revenue sources add up to the Total row for each amount column."""
    is_total = revenue_df['Source'].str.startswith('Total')
    if is_total.sum() != 1:
        return _result('revenue_totals', target, [f"Expected one Total row, found {is_total.sum()}"])
    total = revenue_df[is_total].iloc[0]
    line_items = revenue_df[~is_total][REVENUE_AMOUNT_COLUMNS].fillna(0).sum()
    # The report rounds each line to the dollar, so the sum can drift from the published total by up to $0.50 a line
    tolerance = max(TOLERANCE, 0.5 * (~is_total).sum())
    problems = []
    for column in REVENUE_AMOUNT_COLUMNS:
        published = 0.0 if pd.isna(total[column]) else total[column]
        if abs(line_items[column] - published) > tolerance:
            problems.append(f"{column}: sources sum to {_fmt(line_items[column])}, {total['Source']} is {_fmt(published)}")
    return _result('revenue_totals', target, problems)


# ---------------------------------------------------------------------------
# Validation by input type
# ---------------------------------------------------------------------------

def validate_budget(year_range):
    """Validate one Maine budget against its source PDF."""
    target = f"budget {year_range}"
    processed_path = BUDGET_OUTPUT_DIR / f"{year_range}_budget.pkl"
    exists = check_processed_file_exists(processed_path, target)
    if not exists.passed:
        return [exists]

    processed_df = pd.read_pickle(processed_path)
    first_year, second_year = year_range.split('-')
    end_page = Config.ME_BUDGET_END_PAGES.get(year_range, 8)
    with pdfplumber.open(BUDGET_PDF_DIR / f"{year_range} ME State Budget.pdf") as pdf:
        source_df = parse_me_headline_table(read_me_budget_summary(pdf, end_page), first_year, second_year)
        summary_pages = check_summary_pages(pdf, end_page, target)

    mapping_df = pd.read_csv(Config.DEPARTMENT_MAPPING_FILE)
    departments = _department_rows(processed_df).index.get_level_values('Department').unique()
    return [
        exists,
        check_configured(year_range, 'ME_BUDGET_END_PAGES', Config.ME_BUDGET_END_PAGES, target),
        check_staleness(processed_df, source_df, target),
        summary_pages,
        check_mapping(departments, mapping_df, 'Maine', 'As Reported', target),
        check_department_totals(processed_df, target),
        check_funding_source_totals(processed_df, target),
        check_grand_total(processed_df, target),
    ]


def validate_revenue(year):
    """Validate one year of Maine General Fund revenue against its source PDF."""
    target = f"revenue {year}"
    processed_path = REVENUE_OUTPUT_DIR / f"revenue_{year}.pkl"
    exists = check_processed_file_exists(processed_path, target)
    if not exists.passed:
        return [exists]

    processed_df = pd.read_pickle(processed_path)
    source_df = revenue_table_to_numeric(load_me_general_fund_source_table(year))
    mapping_df = pd.read_csv(Config.REVENUE_SOURCES_MAPPING_FILE)
    sources = processed_df.loc[~processed_df['Source'].str.startswith('Total'), 'Source']
    return [
        exists,
        check_staleness(processed_df.set_index('Source'), source_df.set_index('Source'), target),
        check_mapping(sources, mapping_df, 'Maine', 'As Reported', target),
        check_revenue_totals(processed_df, target),
    ]


def validate_positions(year_range):
    """Validate one Maine budget's position counts against its source PDF. Slow: re-reads the whole PDF."""
    from extract_positions import extract_positions_from_budget_pdf

    target = f"positions {year_range}"
    processed_path = POSITIONS_OUTPUT_DIR / f"{year_range}_positions.pkl"
    exists = check_processed_file_exists(processed_path, target)
    if not exists.passed:
        return [exists]

    processed_df = pd.read_pickle(processed_path)
    source_df = extract_positions_from_budget_pdf(BUDGET_PDF_DIR / f"{year_range} ME State Budget.pdf")
    mapping_df = pd.read_csv(Config.DEPARTMENT_MAPPING_FILE)
    backhistory_df = pd.read_csv(Config.POSITIONS_BACKHISTORY_FILE)
    positions_names_df = pd.concat([mapping_df, backhistory_df])
    departments = processed_df.index.get_level_values('Department').unique()
    return [
        exists,
        check_configured(year_range, 'ME_POSITION_YEARS', Config.ME_POSITION_YEARS, target),
        check_staleness(processed_df, source_df, target),
        check_mapping(departments, positions_names_df, 'Maine', 'Positions As Reported', target, maps_to='As Reported'),
        # Each backhistory name must point at a department that's in the department mapping
        check_mapping(backhistory_df['As Reported'], mapping_df, 'Maine', 'As Reported', f"{target} backhistory"),
    ]


def _budget_year_ranges():
    return sorted(p.stem.split()[0] for p in BUDGET_PDF_DIR.glob("*ME State Budget.pdf"))


def _revenue_years():
    return sorted(p.stem.split()[1] for p in REVENUE_PDF_DIR.glob("FY * Revenue ME.pdf"))


def log_results(results, failures_only=False):
    for result in results:
        if result.passed and failures_only:
            continue
        if result.passed:
            logger.info(f"✓ {result.target}: {result.check}")
        else:
            logger.error(f"✗ {result.target}: {result.check}")
            for problem in result.problems:
                logger.error(f"    {problem}")


def validate_all(budget=True, revenue=True, positions=True, years=None, failures_only=False):
    """Run the selected validations, log each check and return whether all passed.

    Periods come from the source PDFs, so a PDF without a pre-processed file is reported."""
    if not failures_only:
        logger.info("Starting data validation...")
    results = []
    jobs = []
    if budget:
        jobs += [(validate_budget, y) for y in _budget_year_ranges()]
    if revenue:
        jobs += [(validate_revenue, y) for y in _revenue_years()]
    if positions:
        jobs += [(validate_positions, y) for y in _budget_year_ranges()]

    for validate, period in jobs:
        if years and period not in years:
            continue
        try:
            period_results = validate(period)
        except Exception as e:
            period_results = [CheckResult('ran_without_error', f"{validate.__name__} {period}", False, [str(e)])]
        log_results(period_results, failures_only)
        results += period_results

    failed = [r for r in results if not r.passed]
    if failed:
        logger.error(f"✗ {len(failed)} of {len(results)} checks failed")
    else:
        logger.info(f"✓ All {len(results)} checks passed")
    return not failed


def main():
    parser = argparse.ArgumentParser(description='Validate pre-processed data')
    parser.add_argument('--budget', action='store_true', help='Validate Maine budgets')
    parser.add_argument('--revenue', action='store_true', help='Validate General Fund revenue')
    parser.add_argument('--positions', action='store_true', help='Validate positions (slow)')
    parser.add_argument('--year', action='append', help='Only validate this period, e.g. 2026-2027 or 2025. Repeatable')
    parser.add_argument('--failures-only', action='store_true', help='Only print failed checks and the summary')
    args = parser.parse_args()

    run_all = not any([args.budget, args.revenue, args.positions])
    passed = validate_all(
        budget=args.budget or run_all,
        revenue=args.revenue or run_all,
        positions=args.positions or run_all,
        years=args.year,
        failures_only=args.failures_only,
    )
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
