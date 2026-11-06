import pandas as pd
import re

"""Parser for the summary ("Table of Contents") pages of the Maine State Budget PDFs.
Kept free of streamlit so the preprocessing and validation scripts can use it."""

AMOUNT = r'\(?\d{1,3}(?:,\d{3})*\)?'
FUNDING_PATTERN = re.compile(rf'^(.+?)\s+({AMOUNT})\s+({AMOUNT})$')
# pdfplumber sometimes splits the leading digit(s) of a number off with a space, e.g. "GENERAL FUND 1 1,792,254" for 11,792,254
SPLIT_LEADING_DIGITS = re.compile(r'^(.*\D)\s+(\d{1,3})$')


def parse_amount(amount_str):
    """Convert '1,234' to 1234.0 and '(1,234)' to -1234.0."""
    negative = amount_str.startswith('(') and amount_str.endswith(')')
    value = float(amount_str.strip('()').replace(',', ''))
    return -value if negative else value


def rejoin_split_amount(funding_source, first_amount):
    """Undo a number split by a space: ('GENERAL FUND 1', '1,792,254') -> ('GENERAL FUND', '11,792,254')."""
    match = SPLIT_LEADING_DIGITS.match(funding_source)
    if match and not first_amount.startswith('('):
        joined = match.group(2) + first_amount
        if re.fullmatch(AMOUNT, joined):
            return match.group(1).strip(), joined
    return funding_source, first_amount


def parse_me_headline_table(headline_table, first_year, second_year):
    """
    Parse the headline_table from Maine budget text into a DataFrame with columns:
    Department | Funding Source | first_year | second_year

    Args:
        headline_table (str): The text containing budget information
        first_year (str): First year column name
        second_year (str): Second year column name

    Returns:
        pd.DataFrame: DataFrame with parsed budget data
    """
    lines = headline_table.strip().split('\n')
    data = []
    current_dept = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line[0].isdigit():
            # New department
            parts = line.split(' ', 1)
            if len(parts) > 1:
                current_dept = parts[1]
            else:
                current_dept = line
        else:
            match = FUNDING_PATTERN.match(line)
            if match:
                # Funding source
                funding_source, first_amount = rejoin_split_amount(match.group(1).strip(), match.group(2))
                data.append({
                    'Department': current_dept,
                    'Funding Source': funding_source,
                    first_year: parse_amount(first_amount),
                    second_year: parse_amount(match.group(3))
                })

    df = pd.DataFrame(data)
    df = df.set_index(['Department', 'Funding Source'])
    return df


def read_me_budget_summary(pdf, end_page):
    """Extract the text of the summary pages (pages 1 through end_page - 1) from an open pdfplumber PDF."""
    return '\n'.join(page.extract_text() for page in pdf.pages[1:end_page])
