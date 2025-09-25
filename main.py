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
    category_mapping_df = load_category_mapping(Config.CATEGORY_MAPPING_FILE)

    me_standardized_df = standardize_budget(me_processed_df, category_mapping_df, 'Maine')
    nh_standardized_df = standardize_budget(nh_as_reported_df, category_mapping_df, 'New Hampshire')

    #######################################################################################################
    # Visualizations
    #######################################################################################################

    #######################################################################################################
    # Title & Intro
    #######################################################################################################

    st.title("Maine State Spending Analysis")

    st.markdown("""
        Context:
            - Maine's budget has been growing rapidly in recent years
            - Data concerning the budget is publicly available, but not easily digestible
            - We wanted to bridge this gap by creating a dashboard to help understand the budget and its growth
        Goals of this dashboard:    
            1. Make it easier to understand where Maine's money is going
            2. Try to give context on whether that spending makes sense
    """)
    
    #######################################################################################################
    # Headline Spending Section
    #######################################################################################################

    st.plotly_chart(plot_budget_and_spending(me_processed_df))

    #######################################################################################################
    # Why is it growing?
    #######################################################################################################

    st.header("Where is Maine Spending $?")

    # TODO: Add in bar chart of biggest departments

    st.plotly_chart(plot_small_departments_summary(me_processed_df))

    st.subheader("Department Deep Dives")

    departments_to_deep_dive = ['DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)', 'DEPARTMENT OF EDUCATION', 'DEPARTMENT OF TRANSPORTATION']

    for department in departments_to_deep_dive:
        deep_dive_expander = st.expander(department, expanded=False)
        with deep_dive_expander:
            fig, ax = plt.subplots(figsize=(6, 6))
            plot_department_breakdown(ax, department, me_processed_df, fred)
            st.pyplot(fig)

    # TODO: Add in deep dive section with way to display funding details for single department

    # TODO: Add in chart of Maine vs New Hampshire

    # TODO: Add in table for Maine vs New Hampshire

    # indexed_growth_fig = plot_maine_total_spending_vs_gdp(me_as_reported_df, fred)
    # st.plotly_chart(indexed_growth_fig)

    # # Create state comparison
    comparison_df_current = (create_state_comparison(Config.YEAR_CURRENT, me_standardized_df, nh_standardized_df) / 1e6).round(0)
    comparison_df_previous = (create_state_comparison(Config.YEAR_PREVIOUS, me_standardized_df, nh_standardized_df) / 1e6).round(0)

    st.plotly_chart(plot_state_comparison(comparison_df_current, comparison_df_previous, Config.YEAR_CURRENT, Config.YEAR_PREVIOUS))

    # Create department breakdown chart
    # fig, ax = plt.subplots(figsize=(10, 6))
    # plot_department_breakdown(ax, 'GRAND TOTALS - ALL DEPARTMENTS', me_as_reported_df, fred)
    # st.pyplot(fig)

    # # Create small departments summary
    # ex_big_df = filter_excluding_major_departments(me_as_reported_df)
    # ex_big_total_df = ex_big_df.xs('DEPARTMENT TOTAL', level='Funding Source')

    # fig = plot_small_departments_summary(ex_big_total_df)
    # fig.write_image('../c_Exploration/small_departments_summary.png', scale=3)
    # print("Saved small departments summary chart")

    # print("Analysis complete! Check c_Exploration/ for generated charts.")

if __name__ == "__main__":
    main()
