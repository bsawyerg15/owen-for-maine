"""
Data container classes for budget analysis data.
"""
from dataclasses import dataclass
import pandas as pd
from .data_processing import create_state_comparison


@dataclass
class BudgetAnalysisData:
    """Container for all budget analysis data with computed properties for dynamic data."""

    # Static data (loaded once at startup)
    me_processed_df: pd.DataFrame
    nh_standardized_df: pd.DataFrame
    me_standardized_df: pd.DataFrame
    economic_index_df: pd.DataFrame
    general_fund_sources_df: pd.DataFrame
    me_standardized_general_fund_sources_df: pd.DataFrame
    nh_standardized_general_fund_sources_df: pd.DataFrame
    department_mapping_df: pd.DataFrame
    revenue_sources_mapping_df: pd.DataFrame
    enrollment_df: pd.DataFrame

    # Dynamic parameters (change with user selections)
    selected_year_current: str
    selected_year_previous: str

    @property
    def comparison_df_current(self) -> pd.DataFrame:
        """Compute comparison dataframe for current year."""
        return create_state_comparison(
            self.selected_year_current,
            self.me_standardized_df,
            self.nh_standardized_df
        )

    @property
    def comparison_df_previous(self) -> pd.DataFrame:
        """Compute comparison dataframe for previous year."""
        return create_state_comparison(
            self.selected_year_previous,
            self.me_standardized_df,
            self.nh_standardized_df
        )
