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

def standardize_budget(as_reported_df, category_mapping_df, state):
    """Standardize budget data using department mapping. Assumes that the input DataFrame is department total."""
    state_mapping_df = category_mapping_df[category_mapping_df['State'] == state][['As Reported', 'Standardized']]

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
