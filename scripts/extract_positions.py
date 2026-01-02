#!/usr/bin/env python3
"""
Position Data Extraction from Maine Budget PDFs

This script extracts position counts from Maine state budget PDFs.
"""

import sys
import os
import re
import pandas as pd
import pdfplumber
from pathlib import Path

# Add project root to path
sys.path.append('.')

from a_Configs.config import Config


def extract_positions_from_budget_pdf(pdf_path):
    """
    Extract position data from a Maine budget PDF.

    Args:
        pdf_path (str or Path): Path to the budget PDF file

    Returns:
        pd.DataFrame: DataFrame with columns:
            - Department: Department name
            - Position_Type: Type of position count (e.g., 'LEGISLATIVE COUNT', 'FTE COUNT')
            - Year1: Position count for first budget year
            - Year2: Position count for second budget year
            - Total: Sum of Year1 and Year2
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Extract year range from filename (e.g., "2024-2025 ME State Budget.pdf" -> "2024-2025")
    filename = pdf_path.stem
    year_range_match = re.match(r'(\d{4}-\d{4})', filename)
    if not year_range_match:
        raise ValueError(f"Could not extract year range from filename: {filename}")

    year_range = year_range_match.group(1)
    first_year, second_year = year_range.split('-')

    # Extract text from all pages (position data is throughout the document)
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages  # All pages
        text_list = [page.extract_text() for page in pages if page.extract_text()]
        full_text = '\n'.join(text_list)

    # Parse the text for position data
    df = parse_positions_text(full_text, first_year, second_year)

    return df


def parse_positions_text(text, first_year, second_year):
    """
    Parse position data from extracted PDF text.

    Args:
        text (str): Full text extracted from PDF
        first_year (str): First budget year
        second_year (str): Second budget year

    Returns:
        pd.DataFrame: Parsed position data
    """
    lines = text.split('\n')
    data = []
    current_dept = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for department totals marker
        if 'DEPARTMENT TOTALS - ALL FUNDS' in line:
            # Department name should be on the previous line
            if i > 0:
                dept_line = lines[i-1].strip()
                # Clean up department name (remove numbers, extra spaces)
                dept_match = re.match(r'^\d+\s*(.+)$', dept_line)
                if dept_match:
                    current_dept = dept_match.group(1).strip()
                else:
                    current_dept = dept_line.strip()

            # Look for position lines after the department totals
            j = i + 1
            dept_positions = []

            while j < len(lines):
                pos_line = lines[j].strip()

                # Stop if we hit the department total (end of department section)
                if 'DEPARTMENT TOTAL - ALL FUNDS' in pos_line:
                    break

                # Check if this line starts with POSITIONS
                if pos_line.upper().startswith('POSITIONS'):
                    # Extract position type and values
                    pos_data = parse_position_line(pos_line, first_year, second_year)
                    if pos_data:
                        dept_positions.append(pos_data)

                j += 1

            # Calculate department totals
            dept_total_year1 = sum(pos[first_year] for pos in dept_positions)
            dept_total_year2 = sum(pos[second_year] for pos in dept_positions)

            # If no positions found for department, add with zeros
            if not dept_positions:
                dept_positions.append({
                    'Position_Type': 'TOTAL POSITIONS',
                    first_year: 0.0,
                    second_year: 0.0
                })
                dept_total_year1 = 0.0
                dept_total_year2 = 0.0

            # Add individual position data
            for pos in dept_positions:
                data.append({
                    'Department': current_dept,
                    'Position_Type': pos['Position_Type'],
                    first_year: pos[first_year],
                    second_year: pos[second_year],
                    'Total': pos[first_year] + pos[second_year]
                })

            # Add department-level total (only if there are actual positions)
            if dept_positions and dept_total_year1 > 0:
                data.append({
                    'Department': current_dept,
                    'Position_Type': 'TOTAL POSITIONS',
                    first_year: dept_total_year1,
                    second_year: dept_total_year2,
                    'Total': dept_total_year1 + dept_total_year2
                })

            # Skip to next department
            i = j
        else:
            i += 1

    df = pd.DataFrame(data)

    # Set index for consistency with other parsers
    if not df.empty:
        df = df.set_index(['Department', 'Position_Type'])

    return df


def parse_position_line(line, first_year, second_year):
    """
    Parse a single position line to extract type and values.

    Args:
        line (str): Line containing position information
        first_year (str): First budget year
        second_year (str): Second budget year

    Returns:
        dict or None: Parsed position data or None if parsing failed
    """
    # Pattern to match "POSITIONS - [TYPE]" followed by two numbers
    # This is flexible to handle different position types and decimal numbers
    pattern = r'POSITIONS\s*-\s*([^-]+?)\s+([0-9,]+\.?\d*)\s+([0-9,]+\.?\d*)'
    match = re.search(pattern, line, re.IGNORECASE)

    if match:
        position_type = match.group(1).strip().upper()
        year1_str = match.group(2).replace(',', '')
        year2_str = match.group(3).replace(',', '')

        try:
            year1_val = float(year1_str)
        except ValueError:
            year1_val = 0.0

        try:
            year2_val = float(year2_str)
        except ValueError:
            year2_val = 0.0

        return {
            'Position_Type': f'POSITIONS - {position_type}',
            first_year: year1_val,
            second_year: year2_val
        }

    return None


def save_positions_to_pickle(pdf_path, output_dir='preprocessed_data/positions'):
    """
    Extract positions from PDF and save as pickle file.

    Args:
        pdf_path (str or Path): Path to the budget PDF
        output_dir (str): Output directory for pickle files
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract year range from filename
    pdf_path = Path(pdf_path)
    year_range = pdf_path.stem.split()[0]  # e.g., "2024-2025"

    # Extract data
    df = extract_positions_from_budget_pdf(pdf_path)

    # Save as pickle
    output_path = output_dir / f"{year_range}_positions.pkl"
    df.to_pickle(output_path)

    print(f"Saved position data to {output_path}")
    return output_path


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description='Extract positions from Maine budget PDFs')
    parser.add_argument('pdf_path', help='Path to the budget PDF file')
    parser.add_argument('--save', action='store_true', help='Save as pickle file')

    args = parser.parse_args()

    if args.save:
        save_positions_to_pickle(args.pdf_path)
    else:
        df = extract_positions_from_budget_pdf(args.pdf_path)
        print(df.head())
        print(f"Total departments: {len(df.index.get_level_values(0).unique())}")
        print(f"Total position types: {len(df)}")
