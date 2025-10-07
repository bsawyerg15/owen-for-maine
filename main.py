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
from b_App.visualizations import *
from a_Configs.config import *
from b_App.streamlit_viz_helper import *

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
    # Input Dataframes
    #######################################################################################################

    me_as_reported_df = load_me_budget_as_reported(budget_to_end_page, Config.DATA_DIR_ME)
    nh_as_reported_df = load_nh_budget_as_reported(budget_years, Config.DATA_DIR_NH)

    me_processed_df = process_me_budget(me_as_reported_df)

    # Standardized Dataframes
    department_mapping_df = load_department_mapping(Config.DEPARTMENT_MAPPING_FILE)

    me_standardized_df = standardize_budget(me_processed_df, department_mapping_df, 'Maine')
    nh_standardized_df = standardize_budget(nh_as_reported_df, department_mapping_df, 'New Hampshire')

    economic_index_df = produce_economic_index_df(fred).sort_values(by='2023', ascending=False)

    # Scatter
    comparison_df_current = (create_state_comparison(Config.YEAR_CURRENT, me_standardized_df, nh_standardized_df))
    comparison_df_previous = (create_state_comparison(Config.YEAR_PREVIOUS, me_standardized_df, nh_standardized_df))

    comparison_through_time_df = create_styled_comparison_through_time(me_standardized_df, nh_standardized_df, Config.YEAR_PREVIOUS, Config.YEAR_CURRENT)

    
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

    st.header("Bird's Eye View")

    st.plotly_chart(plot_spending_vs_econ_index(me_processed_df.loc[('TOTAL', 'GENERAL FUND')], economic_index_df, to_hide=['CPI', 'Maine Population'], funding_source='GENERAL FUND'))

    st.plotly_chart(plot_department_funding_sources('TOTAL', me_processed_df))

    # st.plotly_chart(plot_budget_and_spending(me_processed_df, funding_source='GENERAL FUND', title='General Fund vs Overall Spending'))

    #######################################################################################################
    # Why is it growing?
    #######################################################################################################

    st.markdown("---")
    st.header("Spending Footprint")

    tab1, tab2 = st.tabs(["Total Spending", "General Fund"])

    with tab1:
        render_spending_footprint_tab(me_processed_df, economic_index_df, 'DEPARTMENT TOTAL', department_mapping_df, comparison_df_current, comparison_df_previous, "_tab1")

    with tab2:
        render_spending_footprint_tab(me_processed_df, economic_index_df, 'GENERAL FUND', department_mapping_df, comparison_df_current, comparison_df_previous, "_tab2")


    #######################################################################################################
    # Maine vs New Hampshire Comparison
    #######################################################################################################

    st.markdown("---")
    st.header("Comparison to New Hampshire")

    top_3_departments = comparison_df_current.sort_values(by='ME', ascending=False).iloc[0:3].index.values
    st.plotly_chart(plot_state_comparison_bars(comparison_df_current, comparison_df_previous, Config.YEAR_CURRENT, Config.YEAR_PREVIOUS, top_3_departments, title='ME vs NH: Top Departments & Growth'))

    biggest_underinvestment = ['MILITARY & VETERANS', 'ENERGY', 'ECONOMIC DEVELOPMENT']
    st.plotly_chart(plot_state_comparison_bars(comparison_df_current, comparison_df_previous, Config.YEAR_CURRENT, Config.YEAR_PREVIOUS, biggest_underinvestment, 'ME vs NH: Areas of Largest Underinvestment'))

    st.dataframe(comparison_through_time_df, use_container_width=True)


if __name__ == "__main__":
    main()
