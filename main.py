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

    st.markdown("""
    Mainers - have you ever wondered how your government is spending your tax dollars? The state government publishes this information [here](https://legislature.maine.gov/ofpr/total-state-budget-information/9304), but as far as we can tell, the data is only in 1000 page pdfs that make it hard to understand where the money is going through time or draw conclusions on whether the spending makes sense. 
    The Owen For Maine campaign is bridging this gap by producing the Maine State Budget Tool. The goals of this tool are:
    1.	To make it easier to understand the factual picture of where funds are going and where growth in spending is occurring
    2.	To help folks draw conclusions on whether the growth we’re seeing makes sense by putting the factual picture in context
                
    We want this tool to be as fair and transparent as possible. If you see any issues with how we’re presenting the data or have questions that the tool currently isn’t able to answer, please reach out to someemail@owenformaine.com.
    """)
    
    #######################################################################################################
    # Headline Spending Section
    #######################################################################################################

    st.plotly_chart(plot_spending_vs_econ_index(me_processed_df.loc[('TOTAL', 'DEPARTMENT TOTAL')], economic_index_df, to_hide=['CPI', 'Maine Population']))

    st.plotly_chart(plot_budget_and_spending(me_processed_df))

    #######################################################################################################
    # Why is it growing?
    #######################################################################################################

    st.header("Where is Maine Spending $?")

    col1, col2 = st.columns([1, 1.5])

    st.plotly_chart(produce_department_bar_chart(me_processed_df, '2027', top_n=3, produce_all_others=True, title='Largest Departments (2027)', prior_year='2018'))

    st.plotly_chart(produce_department_bar_chart(me_processed_df, '2027', top_n=10,
                                                     to_exclude=['TOTAL',
                                                                 'DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)',
                                                                 'DEPARTMENT OF EDUCATION',
                                                                 'DEPARTMENT OF TRANSPORTATION'],
                                                                 produce_all_others=True,
                                                                 title='Other Departments',
                                                                 prior_year='2018'))

    st.plotly_chart(plot_small_departments_summary(me_processed_df))

    #######################################################################################################
    # Maine vs New Hampshire Comparison
    #######################################################################################################


    st.plotly_chart(plot_state_comparison_bars(comparison_df_current, comparison_df_previous, Config.YEAR_CURRENT, Config.YEAR_PREVIOUS, top_n=3))

    st.plotly_chart(plot_state_comparison_bars(comparison_df_current, comparison_df_previous, Config.YEAR_CURRENT, Config.YEAR_PREVIOUS, 12, 3))

    st.dataframe(comparison_through_time_df, use_container_width=True)

    #######################################################################################################
    # Deep Dives
    #######################################################################################################

    st.subheader("Department Deep Dives")

    departments_to_deep_dive = ['DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)', 'DEPARTMENT OF EDUCATION', 'DEPARTMENT OF TRANSPORTATION']

    for department in departments_to_deep_dive:
        deep_dive_expander = st.expander(department, expanded=False)
        with deep_dive_expander:
            fig, ax = plt.subplots(figsize=(10, 6))
            plot_department_funding_sources(ax, department, me_processed_df, fred)
            st.pyplot(fig)


if __name__ == "__main__":
    main()
