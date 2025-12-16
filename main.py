#!/usr/bin/env python3
"""
Main script to run the Maine budget analysis pipeline.
This replicates the functionality from maine_budget.ipynb in modular form.
"""


import sys
sys.path.append('.')

import streamlit as st
import matplotlib.pyplot as plt
from fredapi import Fred

# Import our modules
from b_App.data_ingestion import  *
from b_App.data_processing import *
from b_App.data_container import BudgetAnalysisData
from b_App.visualizations import *
from a_Configs.config import *
from b_App.streamlit_viz_helper import *
from b_App.b_1_Ingest.ingest_me_general_fund_sources import create_through_time_general_fund_sources

st.set_page_config(layout="wide")

def main():

    """Execute the streamlit app."""

    # Initialize FRED API client
    fred = Fred(api_key=Config.FRED_API_KEY)

    #######################################################################################################
    # Constants and Configurations
    #######################################################################################################

    budget_to_end_page = Config.ME_BUDGET_END_PAGES
    budget_years = Config.NH_BUDGET_YEARS

    #######################################################################################################
    # Page Parameters
    #######################################################################################################

    # Year selection widgets
    st.sidebar.header("Parameters")
    year_options = [str(year) for year in range(2016, 2028)]
    selected_year_current = st.sidebar.selectbox(
        "Current Year",
        options=year_options,
        index=year_options.index(Config.YEAR_CURRENT) if Config.YEAR_CURRENT in year_options else 0
    )
    selected_year_previous = st.sidebar.selectbox(
        "Previous Year",
        options=year_options,
        index=year_options.index(Config.YEAR_PREVIOUS) if Config.YEAR_PREVIOUS in year_options else 0
    )

    single_chart_ratio = 4

    #######################################################################################################
    # Input Dataframes
    #######################################################################################################

    me_as_reported_df = load_me_budget_as_reported(budget_to_end_page, Config.DATA_DIR_ME)
    nh_as_reported_df = load_nh_budget_as_reported(budget_years, Config.DATA_DIR_NH)

    me_processed_df = process_me_budget(me_as_reported_df)

    # Standardized Dataframes
    department_mapping_df = load_department_mapping(Config.DEPARTMENT_MAPPING_FILE)
    sub_category_map_df = load_department_mapping(Config.SUB_DEPARTMENT_MAPPING_FILE)
    revenue_sources_mapping_df = load_revenue_sources_mapping(Config.REVENUE_SOURCES_MAPPING_FILE)

    me_standardized_df = standardize_budget(me_processed_df, department_mapping_df, sub_category_map_df, 'Maine')
    nh_standardized_df = standardize_budget(nh_as_reported_df, department_mapping_df, sub_category_map_df, 'New Hampshire')

    economic_index_df = produce_economic_index_df(fred).sort_values(by='2023', ascending=False)

    general_fund_sources_df = create_through_time_general_fund_sources()

    nh_general_fund_sources_df = load_nh_general_fund_sources()
    me_standardized_general_fund_sources_df = standardize_revenue_sources(general_fund_sources_df.reset_index(), revenue_sources_mapping_df, 'Maine')
    nh_standardized_general_fund_sources_df = standardize_revenue_sources(nh_general_fund_sources_df.reset_index(), revenue_sources_mapping_df, 'New Hampshire')

    comparison_through_time_df = create_styled_comparison_through_time(me_standardized_df, nh_standardized_df, selected_year_previous, selected_year_current)

    # Department - specific data
    enrollment_df = load_enrollment_data()

    # Create the data container
    data = BudgetAnalysisData(
        me_processed_df=me_processed_df,
        nh_standardized_df=nh_standardized_df,
        me_standardized_df=me_standardized_df,
        economic_index_df=economic_index_df,
        general_fund_sources_df=general_fund_sources_df,
        me_standardized_general_fund_sources_df=me_standardized_general_fund_sources_df,
        nh_standardized_general_fund_sources_df=nh_standardized_general_fund_sources_df,
        department_mapping_df=department_mapping_df,
        revenue_sources_mapping_df=revenue_sources_mapping_df,
        enrollment_df=enrollment_df,
        selected_year_current=selected_year_current,
        selected_year_previous=selected_year_previous
    )

######## Visualizations ###################################################################################

    #######################################################################################################
    # Title & Intro
    #######################################################################################################

    st.title("Maine State Budget Tool")

    st.subheader("By: [Owen For Maine](https://owenformaine.com)")

    st.markdown("""
    When I first sat down to create my plan for Maine, I found that while the state budget is public, the details are buried in [1000-page pdfs](https://legislature.maine.gov/ofpr/total-state-budget-information/9304).
    I realized that if the information is this inaccessible to me, it must be the same for every voter in the state.
    That said, I decided to build a tool to better understand our state’s budget and am releasing it publicly to help voters make more informed decisions this upcoming election.  
                
    I’d like this tool to be as useful and transparent as possible, so if you see any issues or have additional questions that the tool doesn’t answer, please email my team at someemail@owenformaine.com.
    
    Best,
                
    Owen
    """)

    #######################################################################################################
    # Headline Spending Section
    #######################################################################################################

    st.markdown("---")
    st.header("Bird's Eye View")
    
    st.markdown("We’ll start by getting a lay of the land to understand how the budget has changed through time and where the money’s coming from. " \
    "The General Fund referenced below refers to the money the Maine government has to use as they see fit (i.e. not dedicated for a specific purpose). " \
    "This fund is where all of your state income, sales, corporate taxes, etc. go and so the size of this will correspond to how much Maine is levying in taxes. ")

    _, col, button_col = st.columns([1, single_chart_ratio, 1])
    with col:
        st.plotly_chart(plot_spending_vs_econ_index(data, department='TOTAL', funding_source='GENERAL FUND', to_hide=['CPI', 'Maine Population'], start_year=selected_year_previous))
    with button_col:
        with st.popover(" ℹ️ "):
            st.markdown(f"The dashed lines on the chart to the left puts the growth in context. The green line literally means _what would the General Fund size be if the {selected_year_previous} spending grew at the same rate as inflation and population growth?_ " \
                        "Intuitively, you could roughly understand this as the government is providing a similar set of services through time. "\
                        "On the other hand, if it’s growing in line with the red line, you could interpret that as the government is growing as fast as it can be supported because taxes receipts will increases as GDP rises.")

    st.markdown("In addition to the General Fund, there are other sources of funds such as federal funds, highway funds, etc. that need to be used for specific earmarked purposes. " \
    "In general, throughout this analysis, we’ll use either the General Fund or Total Spending to answer questions about the impact of programs on taxes or overall government footprint, respectively. ")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(plot_department_funding_sources(data, 'TOTAL'))

    with col2:
        st.plotly_chart(plot_general_fund_sources(data, make_percent=True))

    # st.plotly_chart(plot_budget_and_spending(me_processed_df, funding_source='GENERAL FUND', title='General Fund vs Overall Spending'))

    #######################################################################################################
    # Why is it growing?
    #######################################################################################################

    st.markdown("---")
    st.header("Spending Footprint")

    tab1, tab2 = st.tabs(["Total Spending", "General Fund"])

    with tab1:
        render_spending_footprint_tab(data, 'DEPARTMENT TOTAL', single_chart_ratio, "_tab1")

    with tab2:
        render_spending_footprint_tab(data, 'GENERAL FUND', single_chart_ratio, "_tab2")


    #######################################################################################################
    # Maine vs New Hampshire Comparison
    #######################################################################################################

    st.markdown("---")
    st.header("Comparison to New Hampshire")

    st.markdown("_**Why compare to New Hampshire?**_ The main question I had when starting to understand Maine's budget was: _Does our spending make sense?_ " \
    "In addition to understanding the changes through time, another way to answer this question is to compare our spending to a similar state. " \
    "New Hampshire is a useful choice because it has similar demographics (including an almost identical populaton) and geographic proximity. " \
    "However, despite these similarities, New Hampshire has better outcomes than us in economic growth and education while keeping cost of living low by imposing no income or sales tax. " \
    "Knowing how our states differ in spending our tax dollars is a useful clue for how we can achieve these outcomes for Maine.")

    _, col, _ = st.columns([1, single_chart_ratio, 1])
    with col:
        # TODO: make years dynamic -- need nh data through time
        st.plotly_chart(plot_revenue_sources_dumbbell(data, me_year='2025', nh_year='2026'))
        st.markdown('<p style="font-size: 12px; color:gray;">NOTE: Data for each state is of different years, but relationships are relatively stable through time. ' \
        'Unrestricted revenue refers to General Fund in Maine and General Fund plus Educational Trust Fund in NH. '\
        'The quantity referenced as NH\'s sales and use tax referes to their Meals and Rooms tax as they don\'t have a general sales tax.</p>', unsafe_allow_html=True)

    _, col, _ = st.columns([1, single_chart_ratio, 1])
    with col:
        departments_sorted = data.comparison_df_current.sort_values(by='ME', ascending=False).index.values
        top_3_departments = [dept for dept in departments_sorted if dept != 'TOTAL'][:3]
        st.plotly_chart(plot_state_comparison_bars(data, departments_to_show=top_3_departments, title='ME vs NH: Top Departments & Growth'))

        departments_to_deep_dive = ['HEALTH & HUMAN'
        ' SERVICES', 'EDUCATION']
        for department in departments_to_deep_dive:
            with st.expander(department, expanded=False):
                st.plotly_chart(plot_enrollment_comparison(data, department))
                st.plotly_chart(plot_budget_per_enrollee_comparison(data, department))


        biggest_underinvestment = (data.comparison_df_current['ME'] - data.comparison_df_current['NH']).sort_values(ascending=True).head(6).index.values
        st.plotly_chart(plot_state_comparison_bars(data, departments_to_show=biggest_underinvestment, title='ME vs NH: Areas of Largest Underinvestment'))

    st.dataframe(comparison_through_time_df, use_container_width=True)



if __name__ == "__main__":
    main()
