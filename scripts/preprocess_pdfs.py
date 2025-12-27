#!/usr/bin/env python3
"""
PDF Pre-processing Pipeline for Maine Budget Data

This script converts PDF files to structured data formats for faster loading.
Run this when new PDFs are added or existing ones are updated.

Usage:
    python scripts/preprocess_pdfs.py              # Process all PDFs
    python scripts/preprocess_pdfs.py --budget-pdfs # Maine budget PDFs only
    python scripts/preprocess_pdfs.py --revenue-pdfs # Revenue PDFs only
    python scripts/preprocess_pdfs.py --validate    # Validate processed data
"""

import sys
import os
import argparse
import logging
from pathlib import Path
import pandas as pd
import pdfplumber
import re
import numpy as np

# Add project root to path
sys.path.append('.')

from a_Configs.config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/preprocessing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def parse_me_headline_table(headline_table, first_year, second_year):
    """
    Parse the headline_table from Maine budget text into a DataFrame.
    Extracted from data_ingestion.py for standalone use.
    """
    lines = headline_table.strip().split('\n')
    data = []
    current_dept = None
    funding_pattern = re.compile(r'^(.+?)\s+(\(?\d{1,3}(?:,\d{3})*\)?)\s+(\(?\d{1,3}(?:,\d{3})*\)?)$')

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
            match = funding_pattern.match(line)
            if match:
                # Funding source
                funding_source = match.group(1).strip()
                amt_first_year_str = match.group(2).replace(',', '').replace('(', '').replace(')', '')
                amt_second_year_str = match.group(3).replace(',', '').replace('(', '').replace(')', '')

                try:
                    amt_first_year = float(amt_first_year_str)
                except ValueError:
                    amt_first_year = 0.0

                try:
                    amt_second_year = float(amt_second_year_str)
                except ValueError:
                    amt_second_year = 0.0

                data.append({
                    'Department': current_dept,
                    'Funding Source': funding_source,
                    first_year: amt_first_year,
                    second_year: amt_second_year
                })

    df = pd.DataFrame(data)
    df = df.set_index(['Department', 'Funding Source'])
    return df


def load_me_general_fund_source_table(year):
    """
    Load and parse Maine General Fund Revenue Sources from PDF.
    Extracted from ingest_me_general_fund_sources.py for standalone use.
    """
    revenue_path = f'{Config.DATA_DIR_GEN_FUND_SOURCES}FY {year} Revenue ME.pdf'

    if not os.path.exists(revenue_path):
        logger.warning(f"Revenue PDF not found: {revenue_path}")
        return pd.DataFrame()

    # Open PDF and extract text from the relevant page
    with pdfplumber.open(revenue_path) as pdf:
        exhibit_i_page = find_exhibit_page(pdf, 'Exhibit I')
        if exhibit_i_page == -1:
            logger.warning(f"Exhibit I not found in {revenue_path}")
            return pd.DataFrame()
        exhibit_i_text = pdf.pages[exhibit_i_page].extract_text()

    # Find table boundaries
    lines = exhibit_i_text.split('\n')
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if line.startswith('Sales and Use Tax'):
            start_idx = i
        if line.startswith('NOTES:'):
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        logger.warning(f"Could not find table boundaries in {revenue_path}")
        return pd.DataFrame()

    # Extract table lines
    table_lines = [line.strip() for line in lines[start_idx:end_idx] if line.strip()]

    # Process table lines into DataFrame
    data = []
    for line in table_lines:
        # Remove unwanted characters and split
        line = line.replace('$ ', '').replace('%', '').replace(',', '').replace('( ', '(').replace(' )', ')')
        line = re.sub(r'(?<![\d.])\b(\d)\s+(\d+)\b', r'\1\2', line) # Fix spaces in numbers
        line = line.split()
        line_values = line[len(line) - 9:] # Always 9 numerical columns

        clean_values = ['-' + value[1:-1] if value.startswith('(') and value.endswith(')') else value for value in line_values ]
        clean_values = [np.nan if value == '-' or value == '' else value for value in clean_values]

        source = ' '.join(line[0:len(line) - 9])
        clean_values = [source] + clean_values
        data.append(clean_values)

    columns = ['Source', 'Month Actual', 'Month Budget', 'Month Variance', 'Month % Variance',
               'FYTD Actual', 'FYTD Budget', 'FYTD Variance', 'FYTD % Variance', 'Total Budgeted FY']
    return pd.DataFrame(data, columns=columns)


def find_exhibit_page(pdf, exhibit_name):
    """Find the page containing the specified exhibit."""
    for i, page in enumerate(pdf.pages):
        lines = page.extract_text_lines()
        first_line = lines[0]['text'] if lines else ""
        if first_line.endswith(exhibit_name) or first_line.endswith(exhibit_name.upper()):
            return i
    return -1


def preprocess_budget_pdfs():
    """Process all Maine budget PDFs and save as Parquet files."""
    logger.info("Starting Maine budget PDF pre-processing...")

    pdf_dir = Path("z_Data/ME")
    output_dir = Path("preprocessed_data/budgets")
    output_dir.mkdir(parents=True, exist_ok=True)

    processed_count = 0
    for pdf_file in pdf_dir.glob("*ME State Budget.pdf"):
        try:
            # Extract year from filename (e.g., "2016-2017 ME State Budget.pdf")
            year_range = pdf_file.stem.split()[0]  # "2016-2017"
            first_year, second_year = year_range.split('-')

            logger.info(f"Processing {pdf_file.name}...")

            # Parse PDF using existing logic
            with pdfplumber.open(pdf_file) as pdf:
                # Get pages based on config
                end_page = Config.ME_BUDGET_END_PAGES.get(year_range, 8)
                pages = pdf.pages[1:end_page]
                text_list = [page.extract_text() for page in pages]
                headline_table = '\n'.join(text_list)

            # Parse the text into structured data
            df = parse_me_headline_table(headline_table, first_year, second_year)

            if df.empty:
                logger.warning(f"No data extracted from {pdf_file.name}")
                continue

            # Save as Pickle for better compatibility across environments
            output_path = output_dir / f"{year_range}_budget.pkl"
            df.to_pickle(output_path)

            logger.info(f"✓ Processed {pdf_file.name} → {output_path} ({len(df)} rows)")
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing {pdf_file.name}: {e}")
            continue

    logger.info(f"Budget PDF pre-processing complete. Processed {processed_count} files.")


def preprocess_revenue_pdfs():
    """Process all revenue PDFs and save as Pickle files."""
    logger.info("Starting revenue PDF pre-processing...")

    pdf_dir = Path("z_Data/ME General Fund Sources")
    output_dir = Path("preprocessed_data/revenue")
    output_dir.mkdir(parents=True, exist_ok=True)

    processed_count = 0
    for pdf_file in pdf_dir.glob("FY * Revenue ME.pdf"):
        try:
            # Extract year from filename (e.g., "FY 2016 Revenue ME.pdf")
            year = pdf_file.stem.split()[1]  # "2016"

            logger.info(f"Processing {pdf_file.name}...")

            # Parse revenue PDF
            df = load_me_general_fund_source_table(year)

            if df.empty:
                logger.warning(f"No data extracted from {pdf_file.name}")
                continue

            # Convert string columns to numeric types for better compatibility
            for col in df.columns:
                if col != 'Source':  # Keep Source column as string
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Save as pickle with correct data types
            output_path = output_dir / f"revenue_{year}.pkl"
            df.to_pickle(output_path)

            logger.info(f"✓ Processed {pdf_file.name} → {output_path} ({len(df)} rows)")
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing {pdf_file.name}: {e}")
            continue

    logger.info(f"Revenue PDF pre-processing complete. Processed {processed_count} files.")


def validate_processed_data():
    """Validate that processed data matches source PDFs."""
    logger.info("Starting data validation...")

    validation_passed = True

    # Validate budget data
    logger.info("Validating budget data...")
    budget_output_dir = Path("preprocessed_data/budgets")

    for pkl_file in budget_output_dir.glob("*_budget.pkl"):
        try:
            year_range = pkl_file.stem.split('_')[0]  # "2016-2017"
            pdf_path = Path("z_Data/ME") / f"{year_range} ME State Budget.pdf"

            if not pdf_path.exists():
                logger.warning(f"Source PDF not found: {pdf_path}")
                continue

            # Load processed data
            processed_df = pd.read_pickle(pkl_file)

            # Parse source PDF
            first_year, second_year = year_range.split('-')
            with pdfplumber.open(pdf_path) as pdf:
                end_page = Config.ME_BUDGET_END_PAGES.get(year_range, 8)
                pages = pdf.pages[1:end_page]
                text_list = [page.extract_text() for page in pages]
                headline_table = '\n'.join(text_list)

            source_df = parse_me_headline_table(headline_table, first_year, second_year)

            # Compare
            if len(processed_df) != len(source_df):
                logger.error(f"Row count mismatch for {year_range}: {len(processed_df)} vs {len(source_df)}")
                validation_passed = False
                continue

            # Compare total sums
            processed_sum = processed_df.sum().sum()
            source_sum = source_df.sum().sum()

            if abs(processed_sum - source_sum) > 0.01:
                logger.error(".2f")
                validation_passed = False
            else:
                logger.info(f"✓ {year_range} validation passed")

        except Exception as e:
            logger.error(f"Error validating {pkl_file.name}: {e}")
            validation_passed = False

    # Validate revenue data
    logger.info("Validating revenue data...")
    revenue_output_dir = Path("preprocessed_data/revenue")

    for pkl_file in revenue_output_dir.glob("revenue_*.pkl"):
        try:
            year = pkl_file.stem.split('_')[1]  # "2016"
            pdf_path = Path("z_Data/ME General Fund Sources") / f"FY {year} Revenue ME.pdf"

            if not pdf_path.exists():
                logger.warning(f"Source PDF not found: {pdf_path}")
                continue

            # Load processed data
            processed_df = pd.read_pickle(pkl_file)

            # Parse source PDF
            source_df = load_me_general_fund_source_table(year)

            # Compare
            if len(processed_df) != len(source_df):
                logger.error(f"Row count mismatch for revenue {year}: {len(processed_df)} vs {len(source_df)}")
                validation_passed = False
                continue

            logger.info(f"✓ Revenue {year} validation passed")

        except Exception as e:
            logger.error(f"Error validating {pkl_file.name}: {e}")
            validation_passed = False

    if validation_passed:
        logger.info("✓ All validations passed!")
    else:
        logger.error("✗ Some validations failed. Check logs for details.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Pre-process Maine budget PDFs')
    parser.add_argument('--budget-pdfs', action='store_true', help='Process Maine budget PDFs only')
    parser.add_argument('--revenue-pdfs', action='store_true', help='Process revenue PDFs only')
    parser.add_argument('--validate', action='store_true', help='Validate processed data only')

    args = parser.parse_args()

    # If no specific args, run everything
    run_all = not any([args.budget_pdfs, args.revenue_pdfs, args.validate])

    try:
        if args.budget_pdfs or run_all:
            preprocess_budget_pdfs()

        if args.revenue_pdfs or run_all:
            preprocess_revenue_pdfs()

        if args.validate or run_all:
            validate_processed_data()

        logger.info("Pre-processing pipeline completed successfully!")

    except Exception as e:
        logger.error(f"Pre-processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
