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
import base64

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
    year_options = [str(year) for year in range(2016, 2027)]
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

    # Load position data for all available years
    me_positions_df = load_me_positions_as_reported(Config.ME_POSITION_YEARS)
    me_positions_df = standardize_positions(me_positions_df, department_mapping_df)

    me_standardized_df = standardize_budget(me_processed_df, department_mapping_df, sub_category_map_df, 'Maine')
    nh_standardized_df = standardize_budget(nh_as_reported_df, department_mapping_df, sub_category_map_df, 'New Hampshire')

    raw_economic_df = get_economic_indicators_df(fred)
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
        me_positions_df=me_positions_df,
        raw_economic_df=raw_economic_df,
        economic_index_df=economic_index_df,
        general_fund_sources_df=general_fund_sources_df,
        me_standardized_general_fund_sources_df=me_standardized_general_fund_sources_df,
        nh_standardized_general_fund_sources_df=nh_standardized_general_fund_sources_df,
        department_mapping_df=department_mapping_df,
        sub_category_map_df=sub_category_map_df,
        revenue_sources_mapping_df=revenue_sources_mapping_df,
        enrollment_df=enrollment_df,
        selected_year_current=selected_year_current,
        selected_year_previous=selected_year_previous
    )

    # Load and encode the image for display
    with open("z_Data/owenformaine.png", "rb") as f:
        img_data = base64.b64encode(f.read()).decode()
    img_html = f'<a href="https://owenformaine.com"><img src="data:image/png;base64,{img_data}" style="max-width:100%; height:auto;"></a>'

######## Visualizations ###################################################################################

    #######################################################################################################
    # Title & Intro
    #######################################################################################################

    col1, col2, _ = st.columns([2.5, 1, 0.3])

    with col1:
        st.markdown('')
        st.markdown('')
        st.markdown('')
        st.markdown('')
        st.title("Maine State Budget Tool")

    with col2:
        st.markdown(img_html, unsafe_allow_html=True)

    st.markdown("""
    When I first sat down to create my plan for Maine, I found that while the state budget is public, the details are buried in [1000-page pdfs](https://legislature.maine.gov/ofpr/total-state-budget-information/9304).
    I realized that if the information is this inaccessible to me, it must be the same for every voter in the state.
    That said, I asked my campaign to build a tool to better understand our state’s budget and am releasing it publicly to help voters make more informed decisions this upcoming election.  
                
    I’d like this tool to be as useful and transparent as possible, so if you see any issues or have additional questions that the tool doesn’t answer, please email my team at info@owenformaine.com.
    
    Best,
                
    Owen
    """)

    #######################################################################################################
    # Overview
    #######################################################################################################

    st.markdown("---")
    st.header("What is this tool?")

    st.markdown("""
    We're setting out to answer two questions about Maine's budget:
    1. **Where is our state spending tax dollars?**
    2. **Does this spending make sense?** 
                
    After putting the overall budget in context, to answer these questions, we’ll take a close look at (1) how spending in each department has evolved through time and (2) how our spending in each area compares to New Hampshire. 
    """)

    with st.expander("💡 How to use this tool", expanded=False):
        st.markdown("You’ll notice that the tool is very interactive. " \
        "The charts will update if you change the date parameters and you can change the presentation of the charts by clicking the buttons around it. " \
        "By default, it compares the 2019 budgets to 2026 which corresponds to Mills' time as governor. " \
        "Additionally, if you’re curious to learn more about what a chart shows, click the ℹ️ button next to it for additional color.")

    #######################################################################################################
    # Headline Spending Section
    #######################################################################################################

    st.markdown("---")
    st.header("Bird's Eye View")
    
    headline_chart_explainer = f"We’ll start by getting a lay of the land to understand how the budget has changed through time and where the money’s coming from. " \
                        f"The dashed lines on the chart below puts the budget growth in context. The green line literally means _what would the General Fund size be if the {selected_year_previous} spending grew at the same rate as inflation and population growth?_ " \
                        f"Intuitively, budget growth at the green line would be close to saying the government is providing a similar set of services through time. "\
                        f"On the other hand, if it’s growing in line with the red line, you could interpret that as the government is growing as fast as it can be supported because taxes receipts increase as GDP rises."

    general_fund_explainer = f"The General Fund referenced to the left refers to the money the Maine government has to use as they see fit (i.e. not dedicated for a specific purpose). " \
        "This fund is where all of your state income, sales, corporate taxes, etc. go and so the size of this will correspond to how much Maine is levying in taxes. "

    st.markdown(headline_chart_explainer)

    _, col, button_col = st.columns([1, single_chart_ratio, 1])
    with col:
        st.plotly_chart(plot_spending_vs_econ_index(data, department='TOTAL', funding_source='GENERAL FUND', to_hide=['CPI', 'Maine Population'], to_exclude=['New Hampshire GDP'], start_year=selected_year_previous))
    with button_col:
        with st.popover(" ℹ️ "):
            st.markdown(general_fund_explainer)

    st.markdown(" ")
    st.markdown("In addition to the General Fund, there are other sources of funds such as Federal Funds, Highway Funds, etc. that are required to be used for specific earmarked purposes. " \
    "In general, throughout this analysis, we’ll use either the General Fund or Total Spending to answer questions about the impact of programs on taxes or overall government footprint, respectively. ")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(plot_department_funding_sources(data, 'TOTAL'))
    with col2:
        st.plotly_chart(plot_general_fund_sources(data, make_percent=True))

    #######################################################################################################
    # Why is it growing?
    #######################################################################################################

    st.markdown("---")
    st.header("Spending Footprint")

    st.markdown("This section aims to explain where our government is spending tax dollars and how each department's funding has changed through time. " \
    "You can toggle this section between Total Spending and General Fund spending depending on whether you’re more curious about how the government’s overall footprint has changed or where your state tax dollars are going. ")

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
    "In addition to understanding the changes through time, another way come at this question is to compare our spending to a similar state. " \
    "New Hampshire is a useful choice because it has similar demographics (including an almost identical population size) and geographic proximity. " \
    "However, despite these similarities, New Hampshire has a substaintially stronger economy and better educational outcomes while keeping cost of living low by imposing no income or general sales tax. " \
    "Understanding how our states differ in spending our tax dollars offers a useful clue for how we can build a more prosperous Maine.")

    _, col, _ = st.columns([1, single_chart_ratio, 1])
    with col:
        st.plotly_chart(plot_headline_comparison(data, selected_year_previous, selected_year_current))

    st.markdown("Interestingly, we’re able to see that despite having a similar demographic makeup, the fact that New Hampshire has a stronger economy means it’s able to fund an outsized portion of its General Fund spending with business taxes. " \
    "In contrast, business taxes make up a small portion of Maine’s revenues despite having a lower corporate tax rate than Maine (9% vs 7%).")

    _, col, info_col = st.columns([1, single_chart_ratio, 1])
    with col:
        # TODO: make years dynamic -- need nh data through time
        st.plotly_chart(plot_revenue_sources_dumbbell(data, me_year='2025', nh_year='2026'))
    with info_col:
        with st.popover(" ℹ️ "):
            st.markdown('Data for each state is of different years, but relationships are relatively stable through time. ' \
            'Unrestricted revenue refers to General Fund in Maine and General Fund plus Educational Trust Fund in NH. '\
            'The quantity referenced as NH\'s sales and use tax referes to their Meals and Rooms tax as they don\'t have a general sales tax.')

    _, col, _ = st.columns([1, single_chart_ratio, 1])
    with col:
        departments_sorted = data.comparison_df_current.sort_values(by='ME', ascending=False).index.values
        top_3_departments = [dept for dept in departments_sorted if dept != 'TOTAL'][:3]
        st.plotly_chart(plot_state_comparison_bars(data, departments_to_show=top_3_departments, title='ME vs NH: Top Departments & Growth'))

        # Headline sources

        departments_to_deep_dive = ['HEALTH & HUMAN SERVICES', 'EDUCATION']
        for department in departments_to_deep_dive:
            with st.expander(department, expanded=False):
                st.plotly_chart(plot_enrollment_comparison(data, department))
                st.plotly_chart(plot_budget_per_enrollee_comparison(data, department))


        diff_investment = data.comparison_df_current['ME'] - data.comparison_df_current['NH']

        biggest_overinvestment_ex_healthcare_education = diff_investment.drop(index=['TOTAL', 'HEALTH & HUMAN SERVICES', 'EDUCATION']).sort_values(ascending=False).head(6).index.values
        st.plotly_chart(plot_state_comparison_bars(data, departments_to_show=biggest_overinvestment_ex_healthcare_education, title='ME vs NH: Largest Relative Spending (Ex. Healthcare & Education)'))

        biggest_underinvestment = diff_investment.sort_values(ascending=True).head(6).index.values
        st.plotly_chart(plot_state_comparison_bars(data, departments_to_show=biggest_underinvestment, title='ME vs NH: Areas of Largest Relative Underinvestment'))


    st.markdown("The charts above tried to pop some of the interesting relationships between functions across the state. " \
    "There’s a lot more to explore with some of the smaller functions, so we’re providing all of the total spending data below. " \
    "As a note, because the organizational structures of the governments are different, we had to make some choices around how to map different functions in a standardized way. " \
    "E.g. New Hampshire has separate departments for Police and Police training and we map both to Policing. " \
    "You can see the full mapping below. "\
    "This mapping isn’t going to be perfect, so be skeptical before drawing conclusions and if you notice anything that’s clearly wrong, please reach out to the email in the introduction.")

    st.dataframe(comparison_through_time_df, use_container_width=True)
    st.markdown(f'<div style="text-align: center; font-size: 0.8em;">{SourcesConfig.get_footnotes_superscripts(["maine_legislature", "transparent_nh_expenditure"])}</div>', unsafe_allow_html=True)

    with st.expander("Department Name Mapping", expanded=False):
        st.markdown("These tables show how 'as reported' department and sub-department names from Maine and New Hampshire budgets are standardized for comparison. " \
                    "To see all the departments that we've mapped to a single function, select its name in the dropdown below. " \
                    "In many cases, multiple departments are mapped to the same standardized name either to account for different organizational structures across states or because the department name has changed in the budget through time. " \
                    "There is some art to selecting the mapping to get a useful comparison, but that said if you notice any mappings that seem incorrect, please reach out to info@owenformaine.com so we can fix it.")

        # Filter widget
        department_options = ["ALL"] + sorted(data.department_mapping_df['Standardized'].dropna().astype(str).unique())
        selected_department = st.selectbox("Filter by Function", department_options)

        st.subheader("Department Level Mapping")
        dept_df_filtered = data.department_mapping_df[['State', 'Standardized', 'As Reported']]
        if selected_department != "ALL":
            dept_df_filtered = dept_df_filtered[dept_df_filtered['Standardized'] == selected_department]
        dept_df_filtered = dept_df_filtered.sort_values(['State', 'Standardized']).reset_index(drop=True)
        st.dataframe(dept_df_filtered, use_container_width=True)

        st.subheader("Sub-Department/Funding Source Mapping")
        sub_df_filtered = data.sub_category_map_df[['State', 'Standardized', 'As Reported', 'Funding Source']]
        if selected_department != "ALL":
            sub_df_filtered = sub_df_filtered[sub_df_filtered['Standardized'] == selected_department]
        sub_df_filtered = sub_df_filtered.sort_values(['State', 'As Reported', 'Standardized']).reset_index(drop=True)
        st.dataframe(sub_df_filtered, use_container_width=True)


    st.markdown("---")
    with st.expander("Sources"):
        st.markdown("The data powering this analysis comes from a variety of public sources. In each chart title, there is a link to the relevant sources that went into making that chart.")
        sources = SourcesConfig.SOURCES
        sources_text = "\n\n".join([
            f'<sup><a href="{info["url"]}">{i+1}</a></sup> {info["name"]}'
            for i, (key, info) in enumerate(sources.items())
        ])
        st.markdown(sources_text, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
