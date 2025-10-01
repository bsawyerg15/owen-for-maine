"""
Configuration file for the Owen for Maine project.
Centralized location for all configuration variables and constants.
"""

class Config:
    """Configuration class containing all project settings."""

    # API Keys
    FRED_API_KEY = "902a2e4cf2100e3f1045cfbec0139940"

    # Maine budget configuration
    ME_BUDGET_END_PAGES = {
        "2026-2027": 8,
        "2024-2025": 9,
        "2022-2023": 8,
        "2020-2021": 8,
        "2018-2019": 8,
        "2016-2017": 8
    }

    # New Hampshire budget years
    NH_BUDGET_YEARS = [str(year) for year in range(2016, 2026)]

    # Analysis parameters
    YEAR_CURRENT = '2025'
    YEAR_PREVIOUS = '2018'
    DEPARTMENTS_TO_IGNORE = []  # Add any departments to ignore in comparisons

    # File paths (relative to project root)
    DATA_DIR_ME = 'z_Data/ME/'
    DATA_DIR_NH = 'z_Data/NH/'
    CATEGORY_MAPPING_FILE = 'a_Configs/department_mapping.csv'

    # Output directories
    EXPLORATION_DIR = 'c_Exploration/'

    # Scaling
    DEPARTMENT_SCALE = 1e6  # Scale department budgets to millions
    TOTAL_BUDGET_SCALE = 1e9  # Scale total budgets to billions

    DEPARTMENT_SCALE_LABEL = '$, Millions'
    TOTAL_BUDGET_SCALE_LABEL = '$, Billions'

    DEPARTMENT_SCALE_ROUNDING = 0  # Rounding for department budgets
    TOTAL_BUDGET_SCALE_ROUNDING = 2 # Rounding for total budgets