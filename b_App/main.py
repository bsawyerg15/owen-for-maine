#!/usr/bin/env python3
"""
Main script to run the Maine budget analysis pipeline.
This replicates the functionality from maine_budget.ipynb in modular form.
"""

import matplotlib.pyplot as plt
from fredapi import Fred

# Import our modules
from data_ingestion import (
    load_category_mapping,
    load_me_budget_data,
    load_nh_budget_data,
    get_indexed_fred_series
)
from data_processing import (
    standardize_budget,
    create_state_comparison
)
from visualizations import (
    plot_funding_sources,
    plot_department_breakdown,
    plot_state_comparison,
    plot_small_departments_summary
)
from a_Configs.config import Config

def main():
    """Run the complete budget analysis pipeline."""

    # Initialize FRED API client
    fred = Fred(api_key=Config.FRED_API_KEY)

    # Get configuration values
    budget_to_end_page = Config.ME_BUDGET_END_PAGES
    budget_years = Config.BUDGET_YEARS

    print("Loading data...")

    # Load category mapping
    category_mapping_df = load_category_mapping()

    # Load Maine budget data
    me_as_reported_df = load_me_budget_data(budget_to_end_page)
    print(f"Loaded Maine budget data: {me_as_reported_df.shape}")

    # Load New Hampshire budget data
    nh_as_reported_df = load_nh_budget_data(budget_years)
    print(f"Loaded NH budget data: {nh_as_reported_df.shape}")

    print("Processing data...")

    # # Standardize data
    # me_standardized_df = standardize_budget('Maine', me_as_reported_df, category_mapping_df)
    # nh_standardized_df = standardize_budget('New Hampshire', nh_as_reported_df, category_mapping_df)

    # # Get department totals
    # department_total_df = get_department_totals(me_as_reported_df)
    # print(f"Top departments by 2025 spending:\n{department_total_df.sort_values(by='2025', ascending=False).head()}")

    # print("Generating visualizations...")

    # # Create funding source charts
    # funding_sources = ['DEPARTMENT TOTAL'] + me_as_reported_df.xs('GRAND TOTALS - ALL DEPARTMENTS', level='Department').index.unique().tolist()
    # number_of_sources = len(funding_sources)

    # fig, axes = plt.subplots(number_of_sources, 1, figsize=(10, 6 * number_of_sources))

    # for i, source in enumerate(funding_sources):
    #     plot_funding_sources(axes[i] if number_of_sources > 1 else axes, source, me_as_reported_df, fred)

    # plt.tight_layout()
    # plt.savefig('../c_Exploration/funding_sources_analysis.png', dpi=300, bbox_inches='tight')
    # print("Saved funding sources analysis chart")

    # # Create department breakdown chart
    # fig, ax = plt.subplots(figsize=(10, 6))
    # plot_department_breakdown(ax, 'DEPARTMENT OF TRANSPORTATION', me_as_reported_df, fred)
    # plt.savefig('../c_Exploration/transportation_department_breakdown.png', dpi=300, bbox_inches='tight')
    # print("Saved transportation department breakdown chart")

    # # Create state comparison
    # year_current = Config.YEAR_CURRENT
    # year_previous = Config.YEAR_PREVIOUS
    # departments_to_ignore = Config.DEPARTMENTS_TO_IGNORE

    # comparison_df_current = (create_state_comparison(year_current, me_standardized_df, nh_standardized_df, departments_to_ignore) / 1e6).round(0)
    # comparison_df_previous = (create_state_comparison(year_previous, me_standardized_df, nh_standardized_df, departments_to_ignore) / 1e6).round(0)

    # plot_state_comparison(comparison_df_current, comparison_df_previous, year_current, year_previous)

    # # Create small departments summary
    # ex_big_df = filter_excluding_major_departments(me_as_reported_df)
    # ex_big_total_df = ex_big_df.xs('DEPARTMENT TOTAL', level='Funding Source')

    # fig, ax, ax2 = plot_small_departments_summary(ex_big_total_df)
    # plt.savefig('../c_Exploration/small_departments_summary.png', dpi=300, bbox_inches='tight')
    # print("Saved small departments summary chart")

    # print("Analysis complete! Check c_Exploration/ for generated charts.")

if __name__ == "__main__":
    main()
