import pandas as pd
import re

def parse_headline_table(headline_table):
    """
    Parse the headline_table text into a DataFrame with columns:
    Department | Funding Source | 2023 | 2024

    Args:
        headline_table (str): The text containing budget information

    Returns:
        pd.DataFrame: DataFrame with parsed budget data
    """
    lines = headline_table.strip().split('\n')
    data = []
    current_dept = None
    funding_pattern = re.compile(r'^(.+?)\s+(\d{1,3}(?:,\d{3})*)\s+(\d{1,3}(?:,\d{3})*)$')

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
        elif current_dept:
            match = funding_pattern.match(line)
            if match:
                # Funding source
                funding_source = match.group(1).strip()
                amt_2023_str = match.group(2).replace(',', '')
                amt_2024_str = match.group(3).replace(',', '')

                try:
                    amt_2023 = float(amt_2023_str)
                except ValueError:
                    amt_2023 = 0.0

                try:
                    amt_2024 = float(amt_2024_str)
                except ValueError:
                    amt_2024 = 0.0

                data.append({
                    'Department': current_dept,
                    'Funding Source': funding_source,
                    '2023': amt_2023,
                    '2024': amt_2024
                })
            else:
                # Append to department name
                current_dept += ' ' + line

    df = pd.DataFrame(data)
    return df

# Example usage:
if __name__ == "__main__":
    sample_text = """131st LEGISLATURE, 1st Regular Session
131st LEGISLATURE, 1st Special Session
131st LEGISLATURE, 2nd Regular Session
132nd LEGISLATURE, 1st Regular Session
132nd LEGISLATURE, 1st Special Session
Updated July 31, 2025
Table of Contents
Page Department/Agency 2023-24 2024-25
1 DEPARTMENT OF ADMINISTRATIVE AND FINANCIAL SERVICES
(Includes Departments and Agencies - Statewide)
GENERAL FUND 303,364,875 290,558,426
HIGHWAY FUND 3,018,483 3,321,882
FEDERAL EXPENDITURES FUND 489,350 489,350
FUND FOR A HEALTHY MAINE 0 0
OTHER SPECIAL REVENUE 68,888,949 67,507,917
FEDERAL EXPENDITURES FUND ARP SFR 13,749,675 10,385,118
FEDERAL EXPENDITURES FUND ARP 0 0
FINANCIAL & PERSONNEL SERVICES FUND 29,332,374 30,089,127
POSTAL,PRINTING & SUPPLY FUND 4,199,960 4,276,440
15 OFFICE OF INFORMATION SERVICES
RISK MANAGEMENT FUND 9,661,808 6,187,679
WORKERS COMP. MANAGEMENT FUND 20,283,494 20,721,885
CENTRAL MOTOR POOL 9,834,253 9,872,415
REAL PROPERTY LEASE SERVICES 30,428,200 30,437,129"""

    df = parse_headline_table(sample_text)
    print(df.head())
