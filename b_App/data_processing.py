import pandas as pd
import numpy as np
from .data_ingestion import get_economic_indicators_df
from a_Configs.config import *

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


def standardize_budget_from_sub_departments(as_reported_df, sub_category_map_df, full_state_name):
    """Standardize budget data using sub-department mapping for comparison across States."""
    state_mapping_df = sub_category_map_df[sub_category_map_df['State'] == full_state_name][['As Reported', 'Funding Source', 'Standardized']]

    # Map as reported to standardized names
    standardized_df = as_reported_df.reset_index().merge(state_mapping_df, left_on=['Department', 'Funding Source'], right_on=['As Reported', 'Funding Source'], how='inner')
    standardized_df['Standardized'] = standardized_df['Standardized'].str.upper()
    standardized_df.drop(columns=['Department', 'As Reported', 'Funding Source'], inplace=True)
    standardized_df.rename(columns={'Standardized': 'Department'}, inplace=True)
    standardized_df['Funding Source'] = 'DEPARTMENT TOTAL'
    
    # Sum over any departments that mapped to the same standardized name
    standardized_df = standardized_df.groupby(['Department', 'Funding Source']).sum()

    return standardized_df


def standardize_budget_from_direct_mapping(as_reported_df, category_mapping_df, full_state_name):
    """Standardize budget data using department mapping for comparison across States."""
    state_mapping_df = category_mapping_df[category_mapping_df['State'] == full_state_name][['As Reported', 'Standardized']]

    # Map as reported to standardized names
    standardized_df = as_reported_df.reset_index().merge(state_mapping_df, left_on='Department', right_on='As Reported', how='left')
    standardized_df['Standardized'] = standardized_df['Standardized'].str.upper()

    # Testing for unmapped departments
    if standardized_df['Standardized'].isna().any():
        unmapped_depts = standardized_df[standardized_df['Standardized'].isna()]['Department'].unique()
        print(f"⚠️  Unmapped {full_state_name} departments:")
        [print(f"{dept}") for dept in unmapped_depts]

    standardized_df.drop(columns=['Department', 'As Reported'], inplace=True)
    standardized_df.rename(columns={'Standardized': 'Department'}, inplace=True)

    # Sum over any departments that mapped to the same standardized name
    standardized_df = standardized_df.groupby(['Department', 'Funding Source']).sum()

    return standardized_df    


def identify_double_counted_departments(as_reported_df, sub_category_map_df, full_state_name):
    """ Subtract out the sub-departments that were mapped from totals to avoid double counting """
    state_sub_category_map_df = sub_category_map_df[sub_category_map_df['State'] == full_state_name]
   
    # Identify line items already mapped via sub-departments
    as_reported_df_used = as_reported_df.reset_index().merge(state_sub_category_map_df[['As Reported', 'Funding Source']], left_on=['Department', 'Funding Source'], right_on=['As Reported', 'Funding Source'], how='inner')
    as_reported_df_used.drop(columns=['As Reported'], inplace=True)
    
    # Create total already mapped per department
    totals_already_mapped = as_reported_df_used.drop(columns='Funding Source').set_index('Department').groupby(level=['Department']).sum()
    totals_already_mapped['Funding Source'] = 'DEPARTMENT TOTAL'
    totals_already_mapped = totals_already_mapped.reset_index().set_index(['Department', 'Funding Source'])
    return pd.concat([totals_already_mapped, as_reported_df_used.set_index(['Department', 'Funding Source'])])


def standardize_budget(as_reported_df, category_mapping_df, sub_category_map_df, full_state_name):
    """Standardize budget data using department mapping for comparison across States."""
    
    # Map the exception cases first via sub-departments
    standardized_df_from_sub_departments = standardize_budget_from_sub_departments(as_reported_df, sub_category_map_df, full_state_name)
    
    # Subtract out the sub-departments that were mapped from totals to avoid double counting
    totals_already_mapped = identify_double_counted_departments(as_reported_df, sub_category_map_df, full_state_name)
    remaining_funds_df = as_reported_df.subtract(totals_already_mapped, fill_value=0)

    # Use the unallocated funds to determine the rest of the direct mapping
    standardized_df_from_direct_mapping = standardize_budget_from_direct_mapping(remaining_funds_df, category_mapping_df, full_state_name)

    standardized_df = pd.concat([standardized_df_from_direct_mapping, standardized_df_from_sub_departments])
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
    
    me_standardized_df = (me_standardized_df / Config.DEPARTMENT_SCALE).round(0)  # Scale Maine data to millions
    nh_standardized_df = (nh_standardized_df / Config.DEPARTMENT_SCALE).round(0)  # Scale New Hampshire data to millions

    me_end_totals = me_standardized_df.xs('DEPARTMENT TOTAL', level='Funding Source')[end_year]
    nh_end_totals = nh_standardized_df.xs('DEPARTMENT TOTAL', level='Funding Source')[end_year]

    me_start_totals = me_standardized_df.xs('DEPARTMENT TOTAL', level='Funding Source')[start_year]
    nh_start_totals = nh_standardized_df.xs('DEPARTMENT TOTAL', level='Funding Source')[start_year]

    me_diff_arith = me_end_totals - me_start_totals
    nh_diff_arith = nh_end_totals - nh_start_totals

    me_diff_perc = (me_end_totals - me_start_totals) / me_start_totals * 100
    nh_diff_perc = (nh_end_totals - nh_start_totals) / nh_start_totals * 100

    end_diff = me_end_totals - nh_end_totals
    start_diff = me_start_totals - nh_start_totals
    diff_diff_arith = me_diff_arith - nh_diff_arith

    me_vs_nh_end_perc_diff = (me_end_totals - nh_end_totals) / (nh_end_totals) * 100

    df_me = pd.DataFrame({
        end_year: me_end_totals,
        start_year: me_start_totals,
        f'Change from {start_year}': me_diff_arith,
        '% Change': me_diff_perc
    })

    df_nh = pd.DataFrame({
        end_year: nh_end_totals,
        start_year: nh_start_totals,
        f'Change from {start_year}': nh_diff_arith,
        '% Change': nh_diff_perc
    })

    df_diff = pd.DataFrame({
        end_year: end_diff,
        f'{end_year} (%)': me_vs_nh_end_perc_diff,
        start_year: start_diff,
        f'Growth in Diff': diff_diff_arith
    })

    # Combine into MultiIndex DataFrame
    comparison_df = pd.concat([df_me, df_nh, df_diff], keys=['ME', 'NH', 'ME vs NH'], axis=1)

    comparison_df.sort_values(by=('ME', end_year), ascending=False, inplace=True)

    comparison_df.replace([np.inf, -np.inf], np.nan, inplace=True)

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
