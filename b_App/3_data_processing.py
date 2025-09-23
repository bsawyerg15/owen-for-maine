import pandas as pd

def standardize_me_budget(me_as_reported_df, category_mapping_df):
    """Standardize Maine budget data using department mapping."""
    me_mapping_df = category_mapping_df[category_mapping_df['State'] == 'Maine'][['As Reported', 'Standardized']]

    me_standardized_df = me_as_reported_df.reset_index().merge(me_mapping_df, left_on='Department', right_on='As Reported', how='left')
    me_standardized_df['Standardized'] = me_standardized_df['Standardized'].str.upper()
    me_standardized_df.drop(columns=['Department', 'As Reported'], inplace=True)
    me_standardized_df.rename(columns={'Standardized': 'Department'}, inplace=True)
    me_standardized_df = me_standardized_df.groupby(['Department', 'Funding Source']).sum()

    return me_standardized_df

def standardize_nh_budget(department_total_df, category_mapping_df, state):
    """Standardize budget data using department mapping. Assumes that the input DataFrame is department total."""
    state_mapping_df = category_mapping_df[category_mapping_df['State'] == state][['As Reported', 'Standardized']]

    standardized_df = department_total_df.reset_index().merge(state_mapping_df, left_on='DEPARTMENT', right_on='As Reported', how='left')
    standardized_df['Standardized'] = standardized_df['Standardized'].str.upper()
    standardized_df.drop(columns=['DEPARTMENT', 'As Reported'], inplace=True)
    standardized_df.rename(columns={'Standardized': 'DEPARTMENT'}, inplace=True)
    standardized_df = standardized_df.groupby('DEPARTMENT').sum()

    return standardized_df

def create_state_comparison(year, me_standardized_df, nh_standardized_df, departments_to_ignore=None):
    """Create comparison DataFrame between Maine and New Hampshire budgets for a given year."""
    if departments_to_ignore is None:
        departments_to_ignore = []

    me_totals = me_standardized_df.xs('DEPARTMENT TOTAL', level='Funding Source')[year]
    nh_totals = nh_standardized_df[year]

    comparison_df = pd.DataFrame({
        'ME': me_totals,
        'NH': nh_totals
    }).fillna(0)

    comparison_df = comparison_df.drop(departments_to_ignore)

    return comparison_df

def get_department_totals(me_as_reported_df, funding_source='GENERAL FUND'):
    """Extract department totals for a specific funding source."""
    department_total_df = me_as_reported_df.xs(funding_source, level='Funding Source').fillna(0)
    department_total_df = department_total_df[department_total_df.index != 'GRAND TOTALS - ALL DEPARTMENTS']

    return department_total_df

def filter_excluding_major_departments(me_as_reported_df, major_departments=None):
    """Filter out major departments from the budget data."""
    if major_departments is None:
        major_departments = [
            'DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)',
            'DEPARTMENT OF EDUCATION',
            'DEPARTMENT OF TRANSPORTATION'
        ]

    ex_big_df = me_as_reported_df.reset_index()
    ex_big_df = ex_big_df[~ex_big_df['Department'].isin(major_departments)]
    ex_big_df.set_index(['Department', 'Funding Source'], inplace=True)

    return ex_big_df
