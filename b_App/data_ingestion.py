import pandas as pd
import pdfplumber
import re
from fredapi import Fred
import streamlit as st
from pathlib import Path

@st.cache_data
def load_department_mapping(filepath='../a_Configs/department_mapping.csv'):
    """Load department category mapping from CSV."""
    mapping_df = pd.read_csv(filepath)
    mapping_df['Standardized'] = mapping_df['Standardized'].str.upper()
    return mapping_df


@st.cache_data
def load_revenue_sources_mapping(filepath='../a_Configs/Revenue Sources Map.csv'):
    """Load revenue sources mapping from CSV."""
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


@st.cache_data
def load_budget_pickle_file(filepath):
    """Cache individual Pickle file loading."""
    return pd.read_pickle(filepath)


@st.cache_data
def load_position_pickle_file(filepath):
    """Cache individual position Pickle file loading."""
    return pd.read_pickle(filepath)


def load_me_budget_as_reported(budget_to_end_page, data_dir='../z_Data/ME/'):
    """Load Maine budget data from pre-processed files, with PDF fallback."""
    dfs = []

    for budget_year in budget_to_end_page.keys():
        # Try to load from pre-processed Pickle file first
        processed_path = Path("preprocessed_data/budgets") / f"{budget_year}_budget.pkl"

        if processed_path.exists():
            try:
                # Load from pre-processed file (cached)
                df = load_budget_pickle_file(processed_path)
                dfs.append(df)
                continue
            except Exception as e:
                st.warning(f"Failed to load pre-processed data for {budget_year}, falling back to PDF parsing: {e}")

        # Fallback to PDF parsing
        try:
            end_page = budget_to_end_page[budget_year]
            first_year, second_year = budget_year.split('-')
            pdf_path = Path(data_dir) / f"{budget_year} ME State Budget.pdf"

            if not pdf_path.exists():
                st.error(f"PDF file not found: {pdf_path}")
                continue

            with pdfplumber.open(pdf_path) as pdf:
                pages = pdf.pages[1:end_page]
                text_list = [page.extract_text() for page in pages]
                headline_table = '\n'.join(text_list)

            budget_df = parse_me_headline_table(headline_table, first_year, second_year)
            dfs.append(budget_df)

        except Exception as e:
            st.error(f"Failed to parse PDF for {budget_year}: {e}")
            continue

    if not dfs:
        return pd.DataFrame()

    # Concatenate all DataFrames
    result_df = pd.concat(dfs, axis=1)



    return result_df.sort_index(axis=1)


@st.cache_data
def load_me_positions_as_reported(position_years, data_dir='preprocessed_data/positions'):
    """
    Load Maine position data from pre-processed files.

    Args:
        position_years (list): List of year ranges like ['2016-2017', '2018-2019', ...]
        data_dir (str): Directory containing position pickle files

    Returns:
        pd.DataFrame: DataFrame with departments as index and years as columns
    """
    dfs = []

    for year_range in position_years:
        # Try to load from pre-processed Pickle file
        processed_path = Path(data_dir) / f"{year_range}_positions.pkl"

        if processed_path.exists():
            try:
                # Load from pre-processed file (cached)
                df = load_position_pickle_file(processed_path)

                # Extract TOTAL POSITIONS rows (department-level totals)
                total_positions = df[df.index.get_level_values(1) == 'TOTAL POSITIONS']

                # Reset Position_Type index level to get department as regular index
                total_positions = total_positions.reset_index(level=1, drop=True)

                # Keep only the year columns (exclude 'Total' column which sums Year1+Year2)
                year_cols = [col for col in total_positions.columns if col != 'Total']
                dfs.append(total_positions[year_cols])

            except Exception as e:
                st.warning(f"Failed to load position data for {year_range}: {e}")
                continue
        else:
            st.warning(f"Position data not found for {year_range}: {processed_path}")
            continue

    if not dfs:
        return pd.DataFrame()

    # Concatenate all DataFrames along columns (years)
    result_df = pd.concat(dfs, axis=1)

    # Sort columns by year
    result_df = result_df.sort_index(axis=1)

    return result_df


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


@st.cache_data
def load_nh_budget_as_reported(budget_years, data_dir='../z_Data/NH/'):
    """Load New Hampshire budget CSV files and concatenate into single DataFrame."""
    nh_as_reported_df = pd.DataFrame()

    for year in budget_years:
        df_year = load_and_clean_nh_budget(year, data_dir)
        nh_as_reported_df = pd.concat([nh_as_reported_df, df_year], axis=1)

    return nh_as_reported_df


def get_fred_series(_fred_client, series_id, start_date, freq='YE'):
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
    data = _fred_client.get_series(series_id)
    resampled = data.resample(freq).mean()
    filtered = resampled[resampled.index >= start_date]
    filtered.index = filtered.index.year.astype(str)
    return filtered


@st.cache_data(ttl=86400)  # Cache for 24 hours since economic data doesn't change frequently
def get_economic_indicators_df(_fred_client, start_date='2016'):
    """
    Fetch CPI, Maine GDP, New Hampshire GDP, and Maine residential population data from FRED,
    process them using get_indexed_fred_series, and combine into a single DataFrame.

    Parameters:
    - fred_client: Initialized Fred API object
    - start_date: Start date for filtering (default '2016')
    - base_multiplier: Multiplier for re-indexing (default 100)

    Returns:
    - pd.DataFrame: DataFrame with columns 'CPI', 'Maine_GDP', 'New Hampshire_GDP', 'Maine_Population', indexed by year
    """
    cpi_series = get_fred_series(_fred_client, 'CPIAUCSL', start_date)
    me_gdp_series = get_fred_series(_fred_client, 'MENQGSP', start_date)
    nh_gdp_series = get_fred_series(_fred_client, 'NHNQGSP', start_date)
    pop_series = get_fred_series(_fred_client, 'MEPOP', start_date)

    df = pd.DataFrame({
        'CPI': cpi_series,
        'Maine GDP': me_gdp_series,
        'New Hampshire GDP': nh_gdp_series,
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


@st.cache_data
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


@st.cache_data
def load_nh_general_fund_sources():
    """
    Load New Hampshire General Fund Revenue Sources for 2026 from CSV.

    Returns:
    - pd.DataFrame: DataFrame with 'Source' as index and '2026' as column.
    """
    path = 'z_Data/NH General Fund Sources/NH 2026 Revenue Sources.csv'
    df = pd.read_csv(path)
    df = df[['General and Education Fund Grouping', 'Estimate FY 2026']]
    df = df.rename(columns={'General and Education Fund Grouping': 'Source', 'Estimate FY 2026': '2026'})
    df = df.dropna(subset=['Source'])
    df['Source'] = df['Source'].str.strip()
    df = df[df['Source'] != '']
    df['2026'] = df['2026'].str.replace('$', '').str.replace(',', '').astype(float)
    df = df.set_index('Source')
    return df


@st.cache_data
def load_me_budget_archive(filepath='z_Data/ME/ME Total Budget Archive.csv'):
    """
    Load Maine budget archive data from CSV and restructure to match the main budget DataFrame format.

    Returns:
    - pd.DataFrame: DataFrame with Department and Funding Source as multiindex, years as columns.
    """
    # Load the archive CSV
    df = pd.read_csv(filepath)

    # Clean column names and data
    df.columns = df.columns.str.strip()
    df['FISCAL YEAR'] = df['FISCAL YEAR'].astype(str)

    # Remove commas and convert to float for all fund columns
    fund_columns = ['GENERAL FUND', 'HIGHWAY FUND', 'FEDERAL FUNDS', 'OTHER STATE FUNDS', 'TOTAL EXPENDITURES']
    for col in fund_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('$', '').astype(float)

    # Map funding source names to match current naming conventions
    funding_source_mapping = {
        'GENERAL FUND': 'GENERAL FUND',
        'HIGHWAY FUND': 'HIGHWAY FUND',
        'FEDERAL FUNDS': 'FEDERAL EXPENDITURES FUND',
        'OTHER STATE FUNDS': 'OTHER STATE FUNDS',
        'TOTAL EXPENDITURES': 'DEPARTMENT TOTAL'
    }

    # Melt the DataFrame to create rows for each year and funding source
    df_melted = df.melt(id_vars=['FISCAL YEAR'], value_vars=fund_columns,
                       var_name='Funding Source', value_name='Amount')

    # Map funding source names
    df_melted['Funding Source'] = df_melted['Funding Source'].map(funding_source_mapping)

    # Set Department to 'TOTAL' for all rows
    df_melted['Department'] = 'TOTAL'

    # Pivot to create the multiindex format
    df_pivot = df_melted.pivot_table(
        index=['Department', 'Funding Source'],
        columns='FISCAL YEAR',
        values='Amount',
        aggfunc='first'
    )

    return df_pivot


@st.cache_data
def load_me_supplemental_budget(filepath='z_Data/ME Supplemental 2026-27/supplemental_totals_2026_27.csv'):
    """
    Load Maine supplemental budget data from CSV and restructure to match the main budget DataFrame format.

    Returns:
    - pd.DataFrame: DataFrame with Department and Funding Source as multiindex, years as columns.
    """
    # Load the supplemental CSV
    df = pd.read_csv(filepath)

    # Set the multiindex
    df = df.set_index(['Department', 'Funding Source'])

    # Group by index and sum to handle any duplicates
    df = df.groupby(level=['Department', 'Funding Source']).sum()

    return df
