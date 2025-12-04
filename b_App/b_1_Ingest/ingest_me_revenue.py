import pdfplumber
import pandas as pd
import re
import numpy as np


def find_exhibit_page(pdf, exhibit_name):
    for i, page in enumerate(pdf.pages):
        lines = page.extract_text_lines()
        first_line = lines[0]['text'] if lines else ""
        if first_line.endswith(exhibit_name) or first_line.endswith(exhibit_name.upper()):
            return i
    return -1


def extract_revenue_source_table(year):
    revenue_path = f'../z_Data/ME_Revenue/FY {year} Revenue ME.pdf'

    # Open PDF and extract text from the relevant page
    with pdfplumber.open(revenue_path) as pdf:
        exhibit_i_page = find_exhibit_page(pdf, 'Exhibit I')
        if( exhibit_i_page == -1):
            raise ValueError("Exhibit I page not found.")
        exhibit_i_text = pdf.pages[exhibit_i_page].extract_text()  # Page 6 is index 5

    # Find table boundaries. The first item is always "Sales and Use Tax" and there is always a NOTES: section after the table
    lines = exhibit_i_text.split('\n')
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if line.startswith('Sales and Use Tax'):
            start_idx = i
        if line.startswith('NOTES:'):
            end_idx = i
            break

    # Extract table lines
    table_lines = [line.strip() for line in lines[start_idx:end_idx] if line.strip()]

    # Process table lines into DataFrame
    data = []
    for line in table_lines:
        # Remove unwanted characters and split
        line = line.replace('$ ', '').replace('%', '').replace(',', '').replace('( ', '(').replace(' )', ')')
        line = re.sub(r'(?<![\d.])\b(\d)\s+(\d+)\b', r'\1\2', line) # Fix spaces in numbers that happens pre-2019
        line = line.split()
        line_values = line[len(line) - 9:] # Always 9 numerical columns
    
        clean_values = ['-' + value[1:-1] if value.startswith('(') and value.endswith(')') else value for value in line_values ] # Convert () to negative sign
        clean_values = [np.nan if value == '-' or value == '' else value for value in clean_values] # Convert '-' or '' to NaN
            
        source = ' '.join(line[0:len(line) - 9]) # the non-numerical part is the source name
        clean_values = [source] + clean_values
        data.append(clean_values)

    columns = ['Source', 'Month Actual', 'Month Budget', 'Month Variance', 'Month % Variance', 'FYTD Actual', 'FYTD Budget', 'FYTD Variance', 'FYTD % Variance', 'Total Budgeted FY']
    return pd.DataFrame(data, columns=columns)