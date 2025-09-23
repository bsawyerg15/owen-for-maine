import pandas as pd
import pdfplumber
import re
from fredapi import Fred

def load_category_mapping(filepath='../a_Configs/department_mapping.csv'):
    """Load department category mapping from CSV."""
    mapping_df = pd.read_csv(filepath)
    mapping_df['Standardized'] = mapping_df['Standardized'].str.upper()
    return mapping_df

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


def load_me_budget_as_reported(budget_to_end_page, data_dir='../z_Data/ME/'):
    """Load and parse all Maine budget PDFs into a single DataFrame."""
    me_as_reported_df = pd.DataFrame()

    for budget in budget_to_end_page.keys():
        end_page = budget_to_end_page[budget]
        first_year, second_year = budget.split('-')
        pdf_path = f"{data_dir}{budget} ME State Budget.pdf"

        with pdfplumber.open(pdf_path) as pdf:
            pages = pdf.pages[1:end_page]
            text_list = [page.extract_text() for page in pages]
            headline_table = '\n'.join(text_list)

        budget_df = parse_me_headline_table(headline_table, first_year, second_year)
        me_as_reported_df = pd.concat([me_as_reported_df, budget_df], axis=1)

    return me_as_reported_df.sort_index(axis=1)


def load_and_clean_nh_budget(year, data_dir='../z_Data/NH/'):
    """Load and clean a single New Hampshire budget CSV file. 
       Returns DataFrame with columns: 
       Department | Funding Source | year. 
       Where funding source is always 'DEPARTMENT TOTAL'.
    """
    df = pd.read_csv(f"{data_dir}{year} NH State Expenditure.csv")
    df_cleaned = df.dropna(axis=0, how='all').dropna(axis=1, how='all')
    df_cleaned = df_cleaned.rename(columns={'DEPARTMENT': 'Department', 'APROPRIATION': 'Apropriation'})
    df_cleaned.columns = [col.upper().replace("\n", "").replace("JUNE ", "").replace(r'FY\d{2}', "") for col in df_cleaned.columns]
    df_cleaned.columns = [re.sub(r"FY\d{2} ", "", col).lstrip() for col in df_cleaned.columns]
    df_cleaned['Funding Source'] = 'DEPARTMENT TOTAL'

    df_appr = df_cleaned[['Department', 'Funding Source', 'Apropriation']]
    df_appr = df_appr.rename(columns={'Apropriation': year})
    df_appr[year] = df_appr[year].astype(str).str.replace(",", "").astype(float)
    df_appr['Department'] = df_appr['Department'].str.strip()

    df_appr.set_index(('Department', 'Funding Source'), inplace=True)
    return df_appr


def load_nh_budget_as_reported(budget_years, data_dir='../z_Data/NH/'):
    """Load New Hampshire budget CSV files and concatenate into single DataFrame."""
    nh_as_reported_df = pd.DataFrame()

    for year in budget_years:
        df_year = load_and_clean_nh_budget(year, data_dir)
        nh_as_reported_df = pd.concat([nh_as_reported_df, df_year], axis=1)

    return nh_as_reported_df


def get_indexed_fred_series(fred_client, series_id, start_date, base_multiplier, freq='YE'):
    """
    Fetch FRED series data, downsample to specified frequency, filter by date,
    index relative to first value, convert index to year strings, and re-index with multiplier.

    Parameters:
    - fred_client: Initialized Fred API object
    - series_id: FRED series identifier (e.g., 'CPIAUCSL')
    - start_date: Start date for filtering (default '2016')
    - base_multiplier: Multiplier for re-indexing (default 8.2)
    - freq: Resampling frequency (default 'YE' for yearly, use 'M' for monthly)

    Returns:
    - pandas.Series: Processed and re-indexed series
    """
    data = fred_client.get_series(series_id)
    resampled = data.resample(freq).mean()
    filtered = resampled[resampled.index >= start_date]
    indexed = filtered / filtered.iloc[0]
    indexed.index = indexed.index.year.astype(str)
    reindexed = indexed * base_multiplier
    return reindexed
