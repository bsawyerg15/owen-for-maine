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
from b_App.data_ingestion import (
    load_category_mapping,
    load_me_budget_as_reported,
    load_nh_budget_as_reported,
    get_indexed_fred_series
)
from b_App.data_processing import (
    standardize_budget,
    create_state_comparison
)
from b_App.visualizations import (
    plot_funding_sources,
    plot_department_breakdown,
    plot_state_comparison,
    plot_small_departments_summary,
    plot_maine_total_spending_vs_gdp
)
from a_Configs.config import Config

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

    # Standardized Dataframes
    category_mapping_df = load_category_mapping(Config.CATEGORY_MAPPING_FILE)

    me_standardized_df = standardize_budget(me_as_reported_df, category_mapping_df, 'Maine')
    nh_standardized_df = standardize_budget(nh_as_reported_df, category_mapping_df, 'New Hampshire')

    #######################################################################################################
    # Visualizations
    #######################################################################################################

    # Create total funding chart

    indexed_growth_fig = plot_maine_total_spending_vs_gdp(me_as_reported_df, fred)
    st.plotly_chart(indexed_growth_fig)

    # # Create state comparison
    year_current = Config.YEAR_CURRENT
    year_previous = Config.YEAR_PREVIOUS

    comparison_df_current = (create_state_comparison(year_current, me_standardized_df, nh_standardized_df) / 1e6).round(0)
    comparison_df_previous = (create_state_comparison(year_previous, me_standardized_df, nh_standardized_df) / 1e6).round(0)

    fig = plot_state_comparison(comparison_df_current, comparison_df_previous, year_current, year_previous)
    st.plotly_chart(fig)

    # Create department breakdown chart
    fig, ax = plt.subplots(figsize=(10, 6))
    plot_department_breakdown(ax, 'GRAND TOTALS - ALL DEPARTMENTS', me_as_reported_df, fred)
    st.pyplot(fig)

    # # Create small departments summary
    # ex_big_df = filter_excluding_major_departments(me_as_reported_df)
    # ex_big_total_df = ex_big_df.xs('DEPARTMENT TOTAL', level='Funding Source')

    # fig, ax, ax2 = plot_small_departments_summary(ex_big_total_df)
    # plt.savefig('../c_Exploration/small_departments_summary.png', dpi=300, bbox_inches='tight')
    # print("Saved small departments summary chart")

    # print("Analysis complete! Check c_Exploration/ for generated charts.")

if __name__ == "__main__":
    main()
