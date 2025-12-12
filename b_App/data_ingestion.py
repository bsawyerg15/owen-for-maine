import pandas as pd
import pdfplumber
import re
from fredapi import Fred

def load_department_mapping(filepath='../a_Configs/department_mapping.csv'):
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
    df_cleaned.columns = [col.upper().replace("\n", "").replace("JUNE ", "").replace(r'FY\d{2}', "") for col in df_cleaned.columns]
    df_cleaned.columns = [re.sub(r"FY\d{2} ", "", col).lstrip() for col in df_cleaned.columns]
    df_cleaned['Funding Source'] = 'DEPARTMENT TOTAL'
    df_cleaned.rename(columns={'DEPARTMENT': 'Department', 'APPROPRIATION': 'Appropriation'}, inplace=True)

    df_appr = df_cleaned[['Department', 'Funding Source', 'Appropriation']]
    df_appr = df_appr.rename(columns={'Appropriation': year})
    df_appr[year] = df_appr[year].astype(str).str.replace(",", "").astype(float)
    df_appr['Department'] = df_appr['Department'].str.strip()

    df_appr.set_index(['Department', 'Funding Source'], inplace=True)
    return df_appr


def load_nh_budget_as_reported(budget_years, data_dir='../z_Data/NH/'):
    """Load New Hampshire budget CSV files and concatenate into single DataFrame."""
    nh_as_reported_df = pd.DataFrame()

    for year in budget_years:
        df_year = load_and_clean_nh_budget(year, data_dir)
        nh_as_reported_df = pd.concat([nh_as_reported_df, df_year], axis=1)

    return nh_as_reported_df


def get_fred_series(fred_client, series_id, start_date, freq='YE'):
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
    filtered.index = filtered.index.year.astype(str)
    return filtered


def get_economic_indicators_df(fred_client, start_date='2016'):
    """
    Fetch CPI, Maine GDP, and Maine residential population data from FRED,
    process them using get_indexed_fred_series, and combine into a single DataFrame.

    Parameters:
    - fred_client: Initialized Fred API object
    - start_date: Start date for filtering (default '2016')
    - base_multiplier: Multiplier for re-indexing (default 100)

    Returns:
    - pd.DataFrame: DataFrame with columns 'CPI', 'Maine_GDP', 'Maine_Population', indexed by year
    """
    cpi_series = get_fred_series(fred_client, 'CPIAUCSL', start_date)
    gdp_series = get_fred_series(fred_client, 'MENQGSP', start_date)
    pop_series = get_fred_series(fred_client, 'MEPOP', start_date)

    df = pd.DataFrame({
        'CPI': cpi_series,
        'Maine GDP': gdp_series,
        'Maine Population': pop_series
    })

    return df.transpose()


def load_medicaid_enrollment(filepath='z_Data/Department Statistics/HHS/MaineCare Enrollment.csv'):
    """
    Load Medicaid enrollment data from CSV into a pandas DataFrame.

    Parameters:
    - filepath (str): Path to the CSV file (default: 'z_Data/Department Statistics/HHS/MaineCare Enrollment.csv')

    Returns:
    - pd.DataFrame: DataFrame with columns ['Year', 'State', 'Department', 'Enrollment']
    """
    df = pd.read_csv(filepath)
    df['Year'] = df['Year'].astype(int).astype(str)
    df['Enrollment'] = df['Enrollment'].astype(float)
    df['Department'] = 'HEALTH & HUMAN SERVICES'
    return df


def load_public_school_enrollment(filepath='z_Data/Department Statistics/Education/Public School Enrollment.csv'):
    """
    Load public school enrollment data from CSV into a pandas DataFrame.

    Parameters:
    - filepath (str): Path to the CSV file (default: 'z_Data/Department Statistics/Education/Public School Enrollment.csv')

    Returns:
    - pd.DataFrame: DataFrame with columns ['Year', 'State', 'Department', 'Enrollment']
    """
    df = pd.read_csv(filepath)
    df = df.rename(columns={'School Year': 'Year', 'Student Count': 'Enrollment'})
    df['Year'] = df['Year'].astype(str)
    df['Enrollment'] = df['Enrollment'].astype(float)
    df['Department'] = 'EDUCATION'
    return df


def load_enrollment_data():
    """
    Load and combine all enrollment data (Medicaid and Public School) into a single DataFrame.

    Returns:
    - pd.DataFrame: DataFrame with columns ['Year', 'State', 'Department', 'Enrollment']
    """
    medicaid_df = load_medicaid_enrollment()
    public_school_df = load_public_school_enrollment()
    combined_df = pd.concat([medicaid_df, public_school_df], ignore_index=True)
    return combined_df
