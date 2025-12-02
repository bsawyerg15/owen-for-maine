import streamlit as st
from b_App.visualizations import *


def render_spending_footprint_tab(me_processed_df, econ_index_df, funding_source, department_mapping_df, comparison_df_current, comparison_df_previous, current_year, prev_year, suffix):
    """Render the spending footprint tab content for a given funding source."""

    st.plotly_chart(produce_department_bar_chart(me_processed_df, current_year, top_n=3, funding_source=funding_source, produce_all_others=True, title='Spending is Dominated by 3 Departments', prior_year=prev_year, econ_index_df=econ_index_df))

    ### Deep Dives into Key Departments
    if funding_source == 'DEPARTMENT TOTAL':
        departments_to_deep_dive = ['DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)', 'DEPARTMENT OF EDUCATION', 'DEPARTMENT OF TRANSPORTATION']
    else:
        departments_to_deep_dive = ['DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)', 'DEPARTMENT OF EDUCATION']

    for department in departments_to_deep_dive:
        department_mapping_row = department_mapping_df[(department_mapping_df['As Reported'] == department) & (department_mapping_df['State'] == 'Maine')]
        standardized_name = department_mapping_row['Standardized'].values[0]
        clean_name = department_mapping_row['Shortened Name'].values[0]

        deep_dive_expander = st.expander(clean_name, expanded=False)
        with deep_dive_expander:
            # Time series of department funding sources
            st.plotly_chart(plot_department_funding_sources(department, me_processed_df), key=f"{department}_funding_{suffix}")

            # Bar chart comparison to NH
            st.plotly_chart(plot_state_single_comparison_bars(comparison_df_current, comparison_df_previous, current_year, prev_year, department_name=standardized_name), key=f"{department}_state_comp_{suffix}")

    # Small Departments Summary
    st.plotly_chart(produce_department_bar_chart(me_processed_df, current_year, top_n=10,
                                                 to_exclude=Config.LARGE_MAINE_DEPARTMENTS,
                                                 funding_source=funding_source,
                                                 produce_all_others=True,
                                                 title=f'Other Departments - {funding_source}',
                                                 prior_year=prev_year,
                                                 econ_index_df=econ_index_df)
                                                 )

    st.plotly_chart(plot_small_departments_summary(me_processed_df, funding_source=funding_source, title='\"Smaller\" Departments are Growing in Number and Size'))

     # Get list of smaller departments (excluding top 3 and TOTAL)
    all_departments_sorted = me_processed_df.xs(funding_source, level='Funding Source').sort_values(by=current_year, ascending=False).index.tolist()
    smaller_departments = [dept for dept in all_departments_sorted if dept not in Config.LARGE_MAINE_DEPARTMENTS]

    deep_dive_expander = st.expander("Deep Dive into Smaller Departments", expanded=False)
    with deep_dive_expander:
        selected_department = st.selectbox(f"Select a Department:", smaller_departments, format_func=lambda x: x.title(), key=f"selectbox{suffix}")

        if selected_department:
            department_mapping_row = department_mapping_df[(department_mapping_df['As Reported'] == selected_department) & (department_mapping_df['State'] == 'Maine')]
            standardized_name = department_mapping_row['Standardized'].values[0]
            clean_name = department_mapping_row['Shortened Name'].values[0]

            # Time series of department funding sources
            st.plotly_chart(plot_department_funding_sources(selected_department, me_processed_df), key=f"{selected_department}_funding_{suffix}")

            # Bar chart comparison to NH
            st.plotly_chart(plot_state_single_comparison_bars(comparison_df_current, comparison_df_previous, current_year, prev_year, department_name=standardized_name), key=f"{selected_department}_state_comp_{suffix}")