import pandas as pd
from .data_ingestion import get_economic_indicators_df

def process_me_budget(me_budget_as_reported_df):
    """Augment Maine budget data with calculated fields. In particular it:
        1. Adds a 'Total' column summing across all funding sources for each department.
        2. Creates a Funding Source "Department Total ex Federal"
    """
    me_budget_clean_totals_df = clean_total_rows(me_budget_as_reported_df)
    me_budget_w_ex_federal = add_department_total_ex_federal(me_budget_clean_totals_df)

    return me_budget_w_ex_federal


def clean_total_rows(as_reported_df):
    """Finding that ingest captures total rows inconsistently, so drop any existing total rows and replace with calculated totals."""
    no_total_df = as_reported_df.drop(index='GRAND TOTALS - ALL DEPARTMENTS', level='Department')
    total_df = no_total_df.groupby(level='Funding Source').sum()
    total_df['Department'] = 'TOTAL'
    total_df = total_df.reset_index().set_index(['Department', 'Funding Source'])

    return pd.concat([no_total_df, total_df]).sort_index()


def add_department_total_ex_federal(df):
    """Add a 'DEPARTMENT TOTAL ex Federal' funding source to each department."""
    # TODO: are there other funding sources we should exclude?
    federal_df = df.xs('FEDERAL EXPENDITURES FUND', level='Funding Source')
    total_df = df.xs('DEPARTMENT TOTAL', level='Funding Source')
    ex_federal_df = (total_df - federal_df).fillna(total_df)
    ex_federal_df['Funding Source'] = 'DEPARTMENT TOTAL ex FEDERAL'
    ex_federal_df = ex_federal_df.reset_index().set_index(['Department', 'Funding Source'])
    return pd.concat([df, ex_federal_df]).sort_index()


def standardize_budget(as_reported_df, category_mapping_df, full_state_name):
    """Standardize budget data using department mapping for comparison across States."""
    state_mapping_df = category_mapping_df[category_mapping_df['State'] == full_state_name][['As Reported', 'Standardized']]

    standardized_df = as_reported_df.reset_index().merge(state_mapping_df, left_on='Department', right_on='As Reported', how='left')
    standardized_df['Standardized'] = standardized_df['Standardized'].str.upper()
    standardized_df.drop(columns=['Department', 'As Reported'], inplace=True)
    standardized_df.rename(columns={'Standardized': 'Department'}, inplace=True)
    standardized_df = standardized_df.groupby(['Department', 'Funding Source']).sum()

    return standardized_df

def create_state_comparison(year, me_standardized_df, nh_standardized_df):
    """Create comparison DataFrame between Maine and New Hampshire budgets for a given year."""
   
    me_totals = me_standardized_df.xs('DEPARTMENT TOTAL', level='Funding Source')[year]
    nh_totals = nh_standardized_df.xs('DEPARTMENT TOTAL', level='Funding Source')[year]

    comparison_df = pd.DataFrame({
        'ME': me_totals,
        'NH': nh_totals
    }).fillna(0)

    return comparison_df


def create_state_comparison_through_time(me_standardized_df, nh_standardized_df, start_year, end_year):
    """Create comparison DataFrame between Maine and New Hampshire budgets for a given year."""
   
    scale = 1e6
    me_standardized_df = (me_standardized_df / scale).round(0)  # Scale Maine data to millions
    nh_standardized_df = (nh_standardized_df / scale).round(0)  # Scale New Hampshire data to millions

    me_end_totals = me_standardized_df.xs('DEPARTMENT TOTAL', level='Funding Source')[end_year]
    nh_end_totals = nh_standardized_df.xs('DEPARTMENT TOTAL', level='Funding Source')[end_year]

    me_start_totals = me_standardized_df.xs('DEPARTMENT TOTAL', level='Funding Source')[start_year]
    nh_start_totals = nh_standardized_df.xs('DEPARTMENT TOTAL', level='Funding Source')[start_year]

    me_diff_arith = me_end_totals - me_start_totals
    nh_diff_arith = nh_end_totals - nh_start_totals

    me_diff_perc = (me_end_totals - me_start_totals) / me_start_totals * 100
    nh_diff_perc = (nh_end_totals - nh_start_totals) / nh_start_totals * 100

    end_diff = me_end_totals - nh_end_totals
    diff_diff_arith = me_diff_arith - nh_diff_arith
    diff_diff_perc = me_diff_perc - nh_diff_perc

    df_me = pd.DataFrame({
        end_year: me_end_totals,
        f'Change from {start_year}': me_diff_arith,
        '% Change': me_diff_perc
    })

    df_nh = pd.DataFrame({
        end_year: nh_end_totals,
        f'Change from {start_year}': nh_diff_arith,
        '% Change': nh_diff_perc
    })

    df_diff = pd.DataFrame({
        end_year: end_diff,
        f'Change from {start_year}': diff_diff_arith,
        '% Change': diff_diff_perc
    })

    # Combine into MultiIndex DataFrame
    comparison_df = pd.concat([df_me, df_nh, df_diff], keys=['ME', 'NH', 'Diff'], axis=1)
    comparison_df[('ME', '% Change')] = comparison_df[('ME', '% Change')].map('{:.1f}%'.format)
    comparison_df[('NH', '% Change')] = comparison_df[('NH', '% Change')].map('{:.1f}%'.format)
    comparison_df[('Diff', '% Change')] = comparison_df[('Diff', '% Change')].map('{:.1f}%'.format)

    comparison_df.sort_values(by=('ME', end_year), ascending=False, inplace=True
                              )

    return comparison_df


def produce_economic_index_df(fred_client, start_year='2016'):
    """Produce DataFrame with economic indicators indexed to start_year."""
    econ_df = get_economic_indicators_df(fred_client, start_year)
    economic_index_df = econ_df.div(econ_df.iloc[:, 0], axis=0)
    economic_index_df = add_cpi_times_pop_growth_index(economic_index_df)
    
    return economic_index_df

def add_cpi_times_pop_growth_index(economic_index_df):
    """Create DataFrame with just CPI and Population growth from economic index DataFrame."""
    cpi_index = economic_index_df.loc['CPI']
    pop_index = economic_index_df.loc['Maine Population']
    cpi_and_pop_growth = (cpi_index * pop_index).to_frame().T
    cpi_and_pop_growth.index = ['CPI & Population Growth']
    return pd.concat([economic_index_df, cpi_and_pop_growth])