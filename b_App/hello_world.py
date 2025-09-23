import streamlit as st
from fredapi import Fred

# Import our modules
from data_ingestion import (
    load_category_mapping,
    load_me_budget_data,
    load_nh_budget_data
)
from data_processing import (
    create_state_comparison
)
from visualizations import plot_state_comparison

# Set page title
st.title("Hello, World! 🌍")

# Add some content
st.write("Welcome to your first Streamlit app!")
st.write("This is a simple hello world application running in the b_App directory.")

# Generate the scatter plot
st.subheader("Maine vs New Hampshire State Budgets")

# Configuration
API_KEY = "902a2e4cf2100e3f1045cfbec0139940"  # Move to environment variable in production
fred = Fred(api_key=API_KEY)

# Maine budget configuration
budget_to_end_page = {
    "2026-2027": 8,
    "2024-2025": 9,
    "2022-2023": 8,
    "2020-2021": 8,
    "2018-2019": 8,
    "2016-2017": 8
}

# Add an interactive element
if st.button("Click me!"):
    st.success("You clicked the button! 🎉")

# Add a sidebar
st.sidebar.header("About")
st.sidebar.write("This app demonstrates basic Streamlit functionality.")
