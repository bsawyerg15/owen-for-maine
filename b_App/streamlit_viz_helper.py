import streamlit as st
from b_App.visualizations import *


def render_spending_footprint_tab(data, funding_source, single_chart_ratio, suffix):
    """Render the spending footprint tab content for a given funding source."""

    _, col, _ = st.columns([1, single_chart_ratio, 1])
    with col:
        st.plotly_chart(produce_department_bar_chart(data, year=data.selected_year_current, top_n=3, funding_source=funding_source, produce_all_others=True, title='Spending is Dominated by 3 Departments', prior_year=data.selected_year_previous))

        ### Deep Dives into Key Departments
        if funding_source == 'DEPARTMENT TOTAL':
            departments_to_deep_dive = ['DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)', 'DEPARTMENT OF EDUCATION', 'DEPARTMENT OF TRANSPORTATION']
        else:
            departments_to_deep_dive = ['DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)', 'DEPARTMENT OF EDUCATION']

        for department in departments_to_deep_dive:
            department_mapping_row = data.department_mapping_df[(data.department_mapping_df['As Reported'] == department) & (data.department_mapping_df['State'] == 'Maine')]
            standardized_name = department_mapping_row['Standardized'].values[0]
            clean_name = department_mapping_row['Shortened Name'].values[0]

            deep_dive_expander = st.expander(clean_name, expanded=False)
            with deep_dive_expander:
                if department == 'DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)':
                    enrollment_dept = 'HEALTH & HUMAN SERVICES'
                elif department == 'DEPARTMENT OF EDUCATION':
                    enrollment_dept = 'EDUCATION'
                else:
                    enrollment_dept = None

                if enrollment_dept:
                    st.plotly_chart(plot_enrollment(data, enrollment_dept, funding_source), key=f"{department}_enrollment_{suffix}")

                # Time series of department funding sources
                st.plotly_chart(plot_department_funding_sources(data, department), key=f"{department}_funding_{suffix}")

                # Bar chart comparison to NH
                st.plotly_chart(plot_state_single_comparison_bars(data, department_name=standardized_name), key=f"{department}_state_comp_{suffix}")

                if enrollment_dept:
                    st.plotly_chart(plot_enrollment_comparison(data, enrollment_dept), key=f"{department}_enrollment_comp_{suffix}")
                    st.plotly_chart(plot_budget_per_enrollee_comparison(data, enrollment_dept), key=f"{department}_budget_per_enrollee_comp_{suffix}")


    bar_col, line_col = st.columns(2)
    with bar_col:
        # Small Departments Summary
        st.plotly_chart(produce_department_bar_chart(data, year=data.selected_year_current, top_n=10,
                                                    to_exclude=Config.LARGE_MAINE_DEPARTMENTS,
                                                    funding_source=funding_source,
                                                    produce_all_others=True,
                                                    title=f'Other Departments - {funding_source}',
                                                    prior_year=data.selected_year_previous)
                                                    )

    with line_col:
        st.plotly_chart(plot_small_departments_summary(data, funding_source=funding_source, title='\"Smaller\" Departments are Growing in Number and Size'))

     # Get list of smaller departments (excluding top 3 and TOTAL)
    all_departments_sorted = data.me_processed_df.xs(funding_source, level='Funding Source').sort_values(by=data.selected_year_current, ascending=False).index.tolist()
    smaller_departments = [dept for dept in all_departments_sorted if dept not in Config.LARGE_MAINE_DEPARTMENTS]


    _, col, _ = st.columns([1, single_chart_ratio, 1])
    with col:
        deep_dive_expander = st.expander("Deep Dive into Smaller Departments", expanded=False)
        with deep_dive_expander:
            selected_department = st.selectbox(f"Select a Department:", smaller_departments, format_func=lambda x: x.title(), key=f"selectbox{suffix}")

            if selected_department:
                department_mapping_row = data.department_mapping_df[(data.department_mapping_df['As Reported'] == selected_department) & (data.department_mapping_df['State'] == 'Maine')]
                standardized_name = department_mapping_row['Standardized'].values[0]
                clean_name = department_mapping_row['Shortened Name'].values[0]

                # Time series of department funding sources
                st.plotly_chart(plot_department_funding_sources(data, selected_department), key=f"{selected_department}_funding_{suffix}")

                # Bar chart comparison to NH
                st.plotly_chart(plot_state_single_comparison_bars(data, department_name=standardized_name), key=f"{selected_department}_state_comp_{suffix}")
