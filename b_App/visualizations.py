import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from b_App.data_ingestion import get_fred_series
from b_App.data_processing import create_state_comparison_through_time
from a_Configs.config import Config
from a_Configs.sources_config import SourcesConfig

# Cache for department mapping to avoid repeated file reads
_DEPARTMENT_MAPPING = None


def _load_department_mapping():
    """Load and cache department mapping for Maine."""
    global _DEPARTMENT_MAPPING
    if _DEPARTMENT_MAPPING is None:
        mapping_df = pd.read_csv('a_Configs/department_mapping.csv')
        # Filter for Maine entries and create lookup dict
        maine_mapping = mapping_df[mapping_df['State'] == 'Maine'][['As Reported', 'Shortened Name']]
        _DEPARTMENT_MAPPING = dict(zip(maine_mapping['As Reported'], maine_mapping['Shortened Name']))
    return _DEPARTMENT_MAPPING

plt.style.use('default')


def plot_budget_and_spending(df, department='TOTAL', funding_source='DEPARTMENT TOTAL ex FEDERAL', title='Maine State Budget and Spending', start_year='2016'):
    
    df = (df / Config.TOTAL_BUDGET_SCALE).round(Config.TOTAL_BUDGET_SCALE_ROUNDING)
    
    spending_name = 'DEPARTMENT TOTAL'

    spending = df.loc[(department, spending_name)]
    budget = df.loc[(department, funding_source)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=spending.index,
        y=spending.values,
        mode='lines',
        name='Total Spending',
        line=dict(color='blue')
    ))
    fig.add_trace(go.Scatter(
        x=budget.index,
        y=budget.values,
        mode='lines',
        name=f'o.w. {funding_source.title()}',
        line=dict(color='red')
    ))

    fig.update_yaxes(title_text=Config.TOTAL_BUDGET_SCALE_LABEL, rangemode='tozero')
    fig.update_xaxes(tickangle=-45)
    fig.update_layout(
        title=title
    )

    return fig


def plot_revenue_sources_dumbbell(data, me_year, nh_year):
    """Create dumbbell plot comparing ME and NH standardized revenue sources as percentages."""

    # Extract data to local variables
    me_sources_df = data.me_standardized_general_fund_sources_df
    nh_sources_df = data.nh_standardized_general_fund_sources_df

    # Get ME 2025 and NH 2026 data
    me_slice = me_sources_df[me_year] if me_year in me_sources_df.columns else me_sources_df.iloc[:, -1]  # Use latest if 2025 not available
    nh_slice = nh_sources_df['2026']

    # Combine into comparison df
    comparison_df = pd.DataFrame({
        'ME': me_slice,
        'NH': nh_slice
    }).fillna(0)

    # Exclude TOTAL row if present
    comparison_df = comparison_df[~comparison_df.index.str.contains('TOTAL', case=False, na=False)]

    # Calculate percentages
    me_total = comparison_df['ME'].sum()
    nh_total = comparison_df['NH'].sum()
    comparison_df['ME_pct'] = (comparison_df['ME'] / me_total * 100).round(1)
    comparison_df['NH_pct'] = (comparison_df['NH'] / nh_total * 100).round(1)

    # Sort by ME percentage ascending
    comparison_df = comparison_df.sort_values('ME_pct', ascending=True)

    fig = go.Figure()

    # Add ME points
    fig.add_trace(go.Scatter(
        y=comparison_df.index,
        x=comparison_df['ME_pct'],
        mode='markers',
        name=f'Maine {me_year}',
        marker=dict(color='blue', size=10),
        text=[f'ME: {val:.1f}%' for val in comparison_df['ME_pct']],
        hoverinfo='text'
    ))

    # Add NH points
    fig.add_trace(go.Scatter(
        y=comparison_df.index,
        x=comparison_df['NH_pct'],
        mode='markers',
        name=f'New Hampshire {nh_year}',
        marker=dict(color='red', size=10),
        text=[f'NH: {val:.1f}%' for val in comparison_df['NH_pct']],
        hoverinfo='text'
    ))

    # Add connecting lines
    for source in comparison_df.index:
        fig.add_trace(go.Scatter(
            y=[source, source],
            x=[comparison_df.loc[source, 'ME_pct'], comparison_df.loc[source, 'NH_pct']],
            mode='lines',
            line=dict(color='gray', width=2),
            showlegend=False,
            hoverinfo='skip'
        ))

    fig.update_layout(
        title=f'ME vs NH Revenue Sources Comparison{SourcesConfig.get_footnotes_superscripts(["maine_dept_financial", "transparent_nh_revenue"])}<br>(Unrestricted Revenue)',
        yaxis_title='Revenue Source',
        xaxis_title='Percentage of General Fund Revenue (%)',
        xaxis=dict(rangemode='tozero'),
        showlegend=True
    )

    return fig


def plot_department_funding_sources(data, department, start_year=None, end_year=None):
    """Create department breakdown chart by funding source."""

    # Extract data to local variables
    me_processed_df = data.me_processed_df
    selected_year_current = data.selected_year_current
    selected_year_previous = data.selected_year_previous

    if start_year is None:
        start_year = selected_year_previous
    if end_year is None:
        end_year = selected_year_current

    department_df = me_processed_df.xs(department, level='Department').fillna(0)
    funding_sources_to_exclude = ['DEPARTMENT TOTAL ex FEDERAL', 'DEPARTMENT TOTAL', 'GRAND TOTALS - ALL DEPARTMENTS']
    df = department_df[~department_df.index.isin(funding_sources_to_exclude)]
    df = df.sort_values(by=end_year, ascending=False)

    department_scale = Config.DEPARTMENT_SCALE if department != 'TOTAL' else Config.TOTAL_BUDGET_SCALE
    department_scale_rounding = Config.DEPARTMENT_SCALE_ROUNDING if department != 'TOTAL' else Config.TOTAL_BUDGET_SCALE_ROUNDING
    department_scale_label = Config.DEPARTMENT_SCALE_LABEL if department != 'TOTAL' else Config.TOTAL_BUDGET_SCALE_LABEL

    df = (df / department_scale).round(department_scale_rounding)

    top_sources = df.index[:5]  # Top 5 sources by latest year value

    fig = go.Figure()

    # Create stacked area plot by adding traces from bottom to top (largest at bottom)
    # Include all sources but only show legend for top 5
    for i, source in enumerate(df.index):
        y_values = df.loc[source].values
        fig.add_trace(go.Scatter(
            x=df.columns,
            y=y_values,
            mode='lines',
            fill='tozeroy' if i == 0 else 'tonexty',
            name=source.title(),
            showlegend=(source in top_sources),
            stackgroup='one'  # Ensures stacking
        ))

    department_name = '' if department == 'TOTAL' else f'{department.title()}'

    # Update layout
    fig.update_layout(
        title=f'{department_name} Spending by Funding Source{SourcesConfig.get_footnotes_superscripts("maine_legislature")}'.strip(),
        xaxis=dict(
            range=[start_year, end_year],
            autorange=False
        ),
        xaxis_title='Fiscal Year',
        yaxis_title=f'Budget ({department_scale_label})'
    )

    # Add grid lines
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='lightgray', gridwidth=1)

    return fig


def plot_department_num_employees(data, department, start_year=None, end_year=None):
    """Create line chart of department positions over time."""

    # Extract data to local variables
    me_positions_df = data.me_positions_df
    selected_year_current = data.selected_year_current
    selected_year_previous = data.selected_year_previous

    if start_year is None:
        start_year = selected_year_previous
    if end_year is None:
        end_year = selected_year_current

    positions_series = me_positions_df.loc[department]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=positions_series.index,
        y=positions_series.values,
        mode='lines',
        name='Positions',
        line=dict(color='blue')
    ))

    department_name = '' if department == 'TOTAL' else f'{department.title()}'

    # Update layout
    fig.update_layout(
        title=f'{department_name} Number of Employees{SourcesConfig.get_footnotes_superscripts("maine_legislature")}'.strip(),
        xaxis=dict(
            range=[start_year, end_year],
            autorange=False
        ),
        xaxis_title='Fiscal Year',
        yaxis_title='Number of Positions'
    )

    # Add grid lines
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='lightgray', gridwidth=1)

    return fig


def plot_general_fund_sources(data, start_year=None, end_year=None, make_percent=False):
    """Create general fund sources breakdown chart."""

    # Extract data to local variables
    general_fund_sources_df = data.general_fund_sources_df.copy()
    selected_year_current = data.selected_year_current
    selected_year_previous = data.selected_year_previous

    if start_year is None:
        start_year = int(selected_year_previous)
    if end_year is None:
        end_year = int(selected_year_current)

    if make_percent:
        general_fund_sources_df = general_fund_sources_df.mask(general_fund_sources_df < 0)
        total_collected = general_fund_sources_df.drop('Total Collected').sum(axis=0)
        general_fund_sources_df = general_fund_sources_df.div(total_collected, axis=1)
    else:
        general_fund_sources_df = (general_fund_sources_df / Config.TOTAL_BUDGET_SCALE).round(Config.TOTAL_BUDGET_SCALE_ROUNDING)

    lastest_year = int(max(general_fund_sources_df.columns))
    last_display_year = min([lastest_year, end_year])

    general_fund_sources_df = general_fund_sources_df.sort_values(by=str(last_display_year), ascending=False)

    sources_to_plot_df = general_fund_sources_df.drop('Total Collected')

    top_sources = sources_to_plot_df.index[:5]  # Top 5 sources by end_year value

    fig = go.Figure()

    # Create stacked area plot by adding traces from bottom to top (largest at bottom)
    # Include all sources but only show legend for top 5
    for i, source in enumerate(sources_to_plot_df.index):
        y_values = sources_to_plot_df.loc[source].values
        fig.add_trace(go.Scatter(
            x=sources_to_plot_df.columns,
            y=y_values,
            mode='lines',
            fill='tozeroy' if i == 0 else 'tonexty',
            name=source.title(),
            showlegend=(source in top_sources),
            stackgroup='one'  # Ensures stacking
        ))

    # Update layout
    fig.update_layout(
        title=f'General Fund Sources{SourcesConfig.get_footnotes_superscripts("maine_dept_financial")}',
        xaxis=dict(
            range=[str(start_year), str(last_display_year)],
            autorange=False
        ),
        xaxis_title='Fiscal Year',
        yaxis_title=f'Budget ({Config.TOTAL_BUDGET_SCALE_LABEL})' if not make_percent else f'% of General Fund Collected'
    )

    # Add grid lines
    fig.update_xaxes(showgrid=False)
    tickformat = ',.1%' if make_percent else None
    fig.update_yaxes(showgrid=True, gridcolor='lightgray', gridwidth=1, tickformat=tickformat)

    return fig


def plot_spending_vs_econ_index(data, department='TOTAL', funding_source='GENERAL FUND', to_hide=[], to_exclude=[], title=None, start_year=None):
    """Create a plotly chart plotting spending series vs each economic index, with first points aligned."""

    # Extract data to local variables
    me_processed_df = data.me_processed_df
    economic_index_df = data.economic_index_df
    economic_index_df = economic_index_df[~economic_index_df.index.isin(to_exclude)]

    spending_series = me_processed_df.loc[(department, funding_source)]
    spending_series = (spending_series / Config.TOTAL_BUDGET_SCALE).round(Config.TOTAL_BUDGET_SCALE_ROUNDING)

    # Determine the first year from the minimum of both series indices/columns
    if not start_year:
        start_year = str(min([int(y) for y in spending_series.index]))

    # Get base value from spending series at first year
    base_value = spending_series.loc[start_year]

    # Re-index economic indices to start at base_value
    econ_reindexed = (economic_index_df.div(economic_index_df[start_year], axis=0) * base_value).round(Config.TOTAL_BUDGET_SCALE_ROUNDING)

    # Create plotly figure
    fig = go.Figure()

    # Add spending series trace
    fig.add_trace(go.Scatter(
        x=spending_series.index,
        y=spending_series.values,
        mode='lines',
        name='Spending' if funding_source == 'TOTAL' else f'{funding_source.title()}',
        line=dict(color='blue')
    ))

    # Colors for economic indices
    colors = ['red', 'green', 'black', 'orange', 'purple', 'brown']

    # Add each economic index trace
    for i, index_name in enumerate(econ_reindexed.index):
        visibility = 'legendonly' if index_name in to_hide else True
        fig.add_trace(go.Scatter(
            x=econ_reindexed.columns,
            y=econ_reindexed.loc[index_name],
            mode='lines',
            name=index_name,
            line=dict(color=colors[i % len(colors)], dash='dash'),
            visible=visibility
        ))

    sources = ['maine_legislature', 'FRED_me_gdp', 'FRED_cpi', 'FRED_me_pop']
    source_superscripts = SourcesConfig.get_footnotes_superscripts(sources)

    if not title:
        title = f'{funding_source.title()} Spending vs Economic Indices<br>(Reindexed to FY {start_year} Spending){source_superscripts}'
    else:
        title = f"{title}{source_superscripts}"

    # Update layout
    fig.update_layout(
        title=title,
        xaxis=dict(
            range=[start_year, spending_series.index[-1]],
            autorange=False
        ),
        xaxis_title='Fiscal Year',
        yaxis_title='Value',
        legend_title='Legend',
    )
    fig.update_yaxes(title_text=Config.TOTAL_BUDGET_SCALE_LABEL)

    return fig


def plot_state_comparison_scatter(comparison_df_current, comparison_df_previous, year_current, year_previous):
    """Create scatter plot comparing ME and NH budgets with connecting lines."""
    fig = go.Figure()

    # Current year trace
    fig.add_trace(go.Scatter(
        x=comparison_df_current['ME'],
        y=comparison_df_current['NH'],
        mode='markers',
        name=f'{year_current}',
        text=comparison_df_current.index
    ))

    # Previous year trace (invisible markers for connecting lines)
    fig.add_trace(go.Scatter(
        x=comparison_df_previous['ME'],
        y=comparison_df_previous['NH'],
        mode='markers',
        name=year_previous,
        marker=dict(opacity=0, color='gray'),
        hovertext=comparison_df_previous.index,
        showlegend=False
    ))

    # Add connecting lines
    for dept in comparison_df_current.index:
        if dept in comparison_df_previous.index:
            fig.add_trace(go.Scatter(
                x=[comparison_df_current.loc[dept, 'ME'], comparison_df_previous.loc[dept, 'ME']],
                y=[comparison_df_current.loc[dept, 'NH'], comparison_df_previous.loc[dept, 'NH']],
                mode='lines',
                name=f'{dept} connection',
                showlegend=False,
                line=dict(color='gray', dash='dot')
            ))

    # Add y=x line
    x_range = np.linspace(
        min(comparison_df_current['ME'].min(), comparison_df_previous['ME'].min()),
        max(comparison_df_current['ME'].max(), comparison_df_previous['ME'].max()),
        100
    )
    fig.add_trace(go.Scatter(
        x=x_range,
        y=x_range,
        mode='lines',
        name='ME = NH Spending',
        line=dict(color='gray', dash='dash')
    ))

    fig.update_layout(
        width=600,
        height=600,
        title=f'Maine vs New Hampshire State Budgets',
        xaxis_title=f'Maine Budget ({Config.DEPARTMENT_SCALE_LABEL})',
        yaxis_title=f'New Hampshire Budget ({Config.DEPARTMENT_SCALE_LABEL})'
    )

    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    fig.show()

    return fig


def plot_state_comparison_bars(data, departments_to_show=[], title=None):
    """Create grouped bar chart comparing ME and NH budgets with prior year dots. If departments_to_show is provided, only those departments are shown in the specified order."""

    # Extract data to local variables
    comparison_df_current = data.comparison_df_current
    comparison_df_previous = data.comparison_df_previous
    selected_year_current = data.selected_year_current
    selected_year_previous = data.selected_year_previous

    fig = go.Figure()

    # Scale values to department scale
    df = (comparison_df_current / Config.DEPARTMENT_SCALE).round(Config.DEPARTMENT_SCALE_ROUNDING)

    # Sort by ME budget descending (largest first)
    df = df.sort_values(by='ME', ascending=False)
    # Filter to specified departments if provided
    if len(departments_to_show) > 0:
        df = df.loc[departments_to_show]

    # Scale and reindex prior year data to match sorted/limited current
    diff_df = comparison_df_current - comparison_df_previous
    diff_df = (diff_df / Config.DEPARTMENT_SCALE).round(Config.DEPARTMENT_SCALE_ROUNDING).reindex(df.index)

    # Clean department labels for x-axis
    x_labels = [clean_department_labels(dept) for dept in df.index]

    # Use numeric positions for precise alignment
    n = len(df)
    x_numeric = list(range(n))

    fig.add_trace(go.Bar(
        x=x_numeric,
        y=df['ME'],
        offset=-0.2,
        width=0.4,
        name=f'ME {selected_year_current}',
        marker_color='blue',
        text=[f'{val:.0f}' for val in df['ME'].values],
        textposition='auto'
    ))

    fig.add_trace(go.Bar(
        x=x_numeric,
        y=df['NH'],
        offset=0.2,
        width=0.4,
        name=f'NH {selected_year_current}',
        marker_color='red',
        text=[f'{val:.0f}' for val in df['NH'].values],
        textposition='auto'
    ))

    # Add prior year dots centered on each bar
    fig.add_trace(go.Scatter(
        x=x_numeric,  # centered on ME bars
        y=diff_df['ME'],
        mode='markers',
        marker=dict(symbol='diamond', color='lightblue', size=8),
        name=f'ME Change from {selected_year_previous}'
    ))

    fig.add_trace(go.Scatter(
        x=[i + 0.4 for i in x_numeric],  # centered on NH bars
        y=diff_df['NH'],
        mode='markers',
        marker=dict(symbol='diamond', color='lightcoral', size=8),
        name=f'NH Change from {selected_year_previous}'
    ))

    # Adjust title based on filtering mode
    if not title:
        title = f'Maine vs New Hampshire State Budgets'
    elif 'Top Departments' in title or 'Areas of Largest' in title:
        title = f"{title}{SourcesConfig.get_footnotes_superscripts(['maine_legislature', 'transparent_nh_expenditure'])}"

    fig.update_layout(
        title=title,
        yaxis_title=f'Budget ({Config.DEPARTMENT_SCALE_LABEL})',
        xaxis=dict(
            tickmode='array',
            tickvals=[i + 0.2 for i in x_numeric],
            ticktext=x_labels,
            tickangle=-45 if len(departments_to_show) > 3 else 0
        )
    )

    return fig


def plot_state_single_comparison_bars(data, department_name):
    """Create bar chart comparing ME and NH budgets for a single department with prior year dots."""

    # Extract data to local variables
    comparison_df_current = data.comparison_df_current
    comparison_df_previous = data.comparison_df_previous
    selected_year_current = data.selected_year_current
    selected_year_previous = data.selected_year_previous

    if department_name not in comparison_df_current.index:
        raise ValueError(f"Department '{department_name}' not found in current data")

    fig = go.Figure()

    # Scale current and prior values
    current_me = (comparison_df_current.loc[department_name, 'ME'] / Config.DEPARTMENT_SCALE).round(Config.DEPARTMENT_SCALE_ROUNDING)
    current_nh = (comparison_df_current.loc[department_name, 'NH'] / Config.DEPARTMENT_SCALE).round(Config.DEPARTMENT_SCALE_ROUNDING)
    prior_me = (comparison_df_previous.loc[department_name, 'ME'] / Config.DEPARTMENT_SCALE).round(Config.DEPARTMENT_SCALE_ROUNDING)
    prior_nh = (comparison_df_previous.loc[department_name, 'NH'] / Config.DEPARTMENT_SCALE).round(Config.DEPARTMENT_SCALE_ROUNDING)

    # Calculate differences for prior year dots
    diff_me = current_me - prior_me
    diff_nh = current_nh - prior_nh

    # Add ME and NH current year bars
    fig.add_trace(go.Bar(
        x=['ME'],
        y=[current_me],
        name=f'ME {selected_year_current}',
        marker_color='blue',
        text=[f'{current_me:.0f}'],
        textposition='auto'
    ))

    fig.add_trace(go.Bar(
        x=['NH'],
        y=[current_nh],
        name=f'NH {selected_year_current}',
        marker_color='red',
        text=[f'{current_nh:.0f}'],
        textposition='auto'
    ))

    # Add prior year change dots
    fig.add_trace(go.Scatter(
        x=['ME'],
        y=[diff_me],
        mode='markers',
        marker=dict(symbol='diamond', color='lightblue', size=8),
        name=f'ME Change from {selected_year_previous}'
    ))

    fig.add_trace(go.Scatter(
        x=['NH'],
        y=[diff_nh],
        mode='markers',
        marker=dict(symbol='diamond', color='lightcoral', size=8),
        name=f'NH Change from {selected_year_previous}'
    ))

    sources = ['maine_legislature', 'transparent_nh_expenditure']
    source_superscripts = SourcesConfig.get_footnotes_superscripts(sources)
    title = f'{department_name.title()}: Maine vs New Hampshire{source_superscripts}'

    fig.update_layout(
        title=title,
        yaxis_title=f'Budget ({Config.DEPARTMENT_SCALE_LABEL})'
    )

    return fig


def plot_small_departments_summary(data, funding_source='DEPARTMENT TOTAL', big_departments=['DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)', 'DEPARTMENT OF EDUCATION', 'DEPARTMENT OF TRANSPORTATION'], title='Summary of Departments ex Health, Education, and Transportation'):
    """Create summary plot for departments excluding major ones."""

    # Extract data to local variables
    me_processed_df = data.me_processed_df

    total_df = me_processed_df.xs(funding_source, level='Funding Source').fillna(0)
    total_df = (total_df / Config.DEPARTMENT_SCALE)
    ex_big_total_df = total_df[~total_df.index.isin(big_departments)]
    ex_big_total_df = ex_big_total_df.replace(0, np.nan)
    mean_small = ex_big_total_df.mean().round(Config.DEPARTMENT_SCALE_ROUNDING)
    count_small = (ex_big_total_df > 0).sum()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=mean_small.index,
        y=mean_small.values,
        mode='lines',
        name='Average Size',
        line=dict(color='blue')
    ))

    fig.add_trace(go.Scatter(
        x=count_small.index,
        y=count_small.values,
        mode='lines',
        name='Count',
        line=dict(color='black'),
        yaxis='y2'
    ))

    sources = ['maine_legislature']
    source_superscripts = SourcesConfig.get_footnotes_superscripts(sources)
    title = f'{title}{source_superscripts}'

    fig.update_layout(
        title=title,
        xaxis_title='Fiscal Year',
        yaxis_title=f'Mean Size ({Config.DEPARTMENT_SCALE_LABEL})',
        yaxis2=dict(
            title='Count',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        xaxis=dict(showgrid=False),
        legend=dict(x=1.05, y=1)
    )

    return fig


def geo_growth_index_helper(series, start, end):
    """Helper to compute growth rate between two years."""
    if start not in series.index or end not in series.index:
        return np.nan
    start_value = series.loc[start]
    end_value = series.loc[end]
    if start_value == 0:
        return np.nan
    return end_value / start_value


def calc_geo_growth_index_w_extension(series, start_year, end_year, lookback_years):
    """Calculates a geometric growth index (ratio) between a start year and end year for a given time series, 
    with the ability to extend the calculation forward when the end year data is missing 
    by using an average growth rate over a specified lookback period."""

    latest_series_value = series.tail(1)
    latest_series_year = latest_series_value.index[0]

    start_year_is_defined = start_year in series.index
    target_year_is_defined = end_year in series.index

    if not target_year_is_defined:
        avg_5_year_growth_index = (geo_growth_index_helper(series, str(int(latest_series_year) - lookback_years), latest_series_year)) ** (1 / lookback_years)

        if start_year_is_defined:
            defined_growth_index = geo_growth_index_helper(series, start_year, latest_series_year)
            num_defined_years = int(latest_series_year) - int(start_year)
            num_undefined_years = int(end_year) - int(latest_series_year)

            return defined_growth_index * (avg_5_year_growth_index ** num_undefined_years)
        else:
            return avg_5_year_growth_index ** (int(end_year) - int(start_year))
    else:
        return geo_growth_index_helper(series, start_year, end_year)
    


def produce_department_bar_chart(data, year=None, top_n=10, funding_source='DEPARTMENT TOTAL', to_exclude=['TOTAL'], produce_all_others=False, prior_year=None, title=None):
    """Produce bar chart of top N departments by spending for a given year."""

    # Extract data to local variables
    me_processed_df = data.me_processed_df
    economic_index_df = data.economic_index_df
    selected_year_current = data.selected_year_current
    selected_year_previous = data.selected_year_previous

    if year is None:
        year = selected_year_current
    if prior_year is None:
        prior_year = selected_year_previous

    # Select the departments and funding for the chart
    total_df = me_processed_df.xs(funding_source, level='Funding Source').fillna(0) / Config.DEPARTMENT_SCALE
    total_df = total_df.round(Config.DEPARTMENT_SCALE_ROUNDING).astype(int)
    years_to_use = [year, prior_year] if prior_year else [year]
    total_for_year_df = total_df[years_to_use].sort_values(by=year, ascending=False)
    total_with_exclusions = total_for_year_df[~total_for_year_df.index.isin(to_exclude)]
    top_departments = total_with_exclusions.head(top_n)
    
    if produce_all_others:
        others_sum = total_with_exclusions.iloc[top_n:].sum()
        top_departments = pd.concat([top_departments, pd.DataFrame([others_sum.values], index=['ALL OTHERS'], columns=top_departments.columns)])

    # Generate CPI + inflation multiplier
    if prior_year:
        cpi_n_pop_growth_series = economic_index_df.loc['CPI & Population Growth'].dropna()

        growth_index = calc_geo_growth_index_w_extension(cpi_n_pop_growth_series, prior_year, year, lookback_years=5)

        department_spending_at_cpi_n_pop_growth = (top_departments[prior_year] * growth_index).round(Config.DEPARTMENT_SCALE_ROUNDING)


    # Create vertical bar chart using plotly.graph_objects for better control over multiline labels
    fig = go.Figure()

    if prior_year:
        fig.add_trace(go.Bar(
            x=list(range(len(top_departments))),
            y=top_departments[prior_year].values,
            text=[f'{val}' for val in top_departments[prior_year].values],
            textposition='auto',
            hovertext=top_departments.index,
            marker_color='lightblue',
            name=f'FY {prior_year}'
        ))

    fig.add_trace(go.Bar(
        x=list(range(len(top_departments))),
        y=top_departments[year].values,
        text=[f'{val}' for val in top_departments[year].values],
        textposition='auto',
        hovertext=top_departments.index,
        marker_color='blue',
        name=f'FY {year}'
    ))

    if prior_year:
        fig.add_trace(go.Scatter(
            x=list(range(len(top_departments))),
            y=department_spending_at_cpi_n_pop_growth.values,
            mode='markers',
            marker=dict(symbol='circle', color='lightblue', size=8),
            name=f'{prior_year} + CPI & Pop. Growth',
            hovertext=top_departments.index
        ))

    # Set x-axis labels with multiline text
    multiline_labels = [clean_department_labels(department) for department in top_departments.index]
    fig.update_xaxes(
        tickmode='array',
        tickvals=list(range(len(top_departments))),
        ticktext=multiline_labels,
        tickangle=-45 if top_n > 4 else 0
    )

    sources = ['maine_legislature', 'FRED_cpi', 'FRED_me_pop']
    source_superscripts = SourcesConfig.get_footnotes_superscripts(sources)
    if not title:
        title = f'{funding_source.title()} Departments by Spending'
    title = f'{title}{source_superscripts}'

    fig.update_yaxes(title_text=f'Spending ({Config.DEPARTMENT_SCALE_LABEL})')
    fig.update_layout(
        title=title,
        showlegend=True,
        height=500,
        barmode='group'
    )

    return fig


def clean_department_labels(text, num_words_per_line=3):
    """
    Clean department labels by using shortened names from mapping and inserting newlines.

    Args:
        text (str): The input department name
        num_words_per_line (int): Number of words per line for formatting

    Returns:
        str: The cleaned and formatted string
    """
    # Load department mapping
    mapping = _load_department_mapping()

    # Use shortened name if available, otherwise use original text
    display_text = mapping.get(text, text)

    # Remove "DEPARTMENT OF " prefix if present
    display_text = display_text.replace('DEPARTMENT OF ', '')

    if num_words_per_line <= 0:
        return display_text

    words = display_text.split()
    if not words:
        return display_text

    lines = []
    for i in range(0, len(words), num_words_per_line):
        lines.append(' '.join(words[i:i+num_words_per_line]))
    return '\n'.join(lines)


def create_styled_comparison_through_time(me_standardized_df, nh_standardized_df, start_year, end_year):
    """Create styled comparison DataFrame between Maine and New Hampshire budgets for a given year."""
    comparison_df = create_state_comparison_through_time(me_standardized_df, nh_standardized_df, start_year, end_year)

    # Apply styling
    unique_levels = set(col[1] for col in comparison_df.columns)
    absmax = {}
    for level in unique_levels:
        cols_in_group = [col for col in comparison_df.columns if col[1] == level]
        all_values = comparison_df[cols_in_group].values.flatten()
        max_abs = max(abs(np.nanmin(all_values)), abs(np.nanmax(all_values)))
        for col in cols_in_group:
            absmax[col] = max_abs

    styler = comparison_df.style
    for col in comparison_df.columns:
        styler = styler.background_gradient(
            subset=[col],
            cmap='RdBu',
            vmin=-absmax[col],
            vmax=absmax[col]
        )

    styler = styler.applymap(lambda v: 'background-color: white' if pd.isna(v) else '')

    formats = {}
    for col in comparison_df.columns:
        if '%' in col[1]:
            formats[col] = lambda x: '-' if pd.isna(x) else f'{x:.1f}%'
        else:
            formats[col] = lambda x: '-' if pd.isna(x) else f'{x:.0f}'
    styler = styler.format(formats)

    return styler


def plot_enrollment(data, department, funding_source='DEPARTMENT TOTAL'):
    """
    Create a line chart for enrollment data and department budget per enrollee.

    Parameters:
    - data: BudgetAnalysisData object containing enrollment_df and me_processed_df
    - department: The enrollment department ('HEALTH & HUMAN SERVICES' or 'EDUCATION')
    - funding_source: The funding source to use for budget calculation (default: 'DEPARTMENT TOTAL')

    Returns:
    - plotly.graph_objects.Figure: The plotly figure
    """

    # Map enrollment department to budget department
    dept_mapping = {
        'HEALTH & HUMAN SERVICES': 'DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)',
        'EDUCATION': 'DEPARTMENT OF EDUCATION'
    }
    budget_dept = dept_mapping[department]

    # Extract data to local variables
    enrollment_df = data.enrollment_df[
        (data.enrollment_df['Department'] == department) &
        (data.enrollment_df['State'] == 'Maine')
    ]
    series = enrollment_df.set_index('Year')['Enrollment']
    selected_year_current = data.selected_year_current
    selected_year_previous = data.selected_year_previous

    # Set start and end years based on data selection
    start_year = selected_year_previous
    end_year = selected_year_current

    # Get department budget data
    dept_budget = data.me_processed_df.loc[(budget_dept, funding_source)]

    # Calculate budget per enrollee
    budget_per_enrollee = (dept_budget / series).round(0)

    # Set titles based on department
    if department == 'HEALTH & HUMAN SERVICES':
        enrollment_name = 'MaineCare Enrollment'
        dept_name = 'DHHS'
        enrollment_source = 'mainecare_enrollment'
    else:
        enrollment_name = 'Public School Enrollment'
        dept_name = department.title()
        enrollment_source = 'me_public_school_enrollment'

    fig = go.Figure()

    # Enrollment trace (primary y-axis)
    fig.add_trace(go.Scatter(
        x=series.index,
        y=series.values,
        mode='lines',
        name=enrollment_name,
        line=dict(color='blue')
    ))

    # Budget per enrollee trace (secondary y-axis)
    fig.add_trace(go.Scatter(
        x=budget_per_enrollee.index,
        y=budget_per_enrollee.values,
        mode='lines',
        name=f'{dept_name} Budget per Enrollee' if department == 'HEALTH & HUMAN SERVICES' else f'{dept_name} Budget per Student',
        line=dict(color='red'),
        yaxis='y2'
    ))

    fig.update_layout(
        title=f'{enrollment_name} and {dept_name} Budget per {"Enrollee" if department == "HEALTH & HUMAN SERVICES" else "Student"} - {funding_source.title()}{SourcesConfig.get_footnotes_superscripts([enrollment_source, "maine_legislature"])}',
        xaxis_title='Fiscal Year',
        yaxis_title='Enrollment',
        yaxis2=dict(
            title=f'Budget per {"Enrollee" if department == "HEALTH & HUMAN SERVICES" else "Student"} ($)',
            overlaying='y',
            side='right',
            showgrid=False,
            rangemode='tozero'
        ),
        xaxis=dict(
            range=[start_year, end_year],
            autorange=False),
        yaxis=dict(rangemode='tozero')
    )

    return fig


def plot_enrollment_comparison(data, department):
    """
    Create a line chart comparing Maine and New Hampshire enrollment over time.

    Parameters:
    - data: BudgetAnalysisData object containing enrollment_df
    - department: The enrollment department ('HEALTH & HUMAN SERVICES' or 'EDUCATION')

    Returns:
    - plotly.graph_objects.Figure: The plotly figure
    """

    # Extract data to local variables
    enrollment_df = data.enrollment_df[data.enrollment_df['Department'] == department]
    selected_year_current = data.selected_year_current
    selected_year_previous = data.selected_year_previous

    # Set start and end years based on data selection
    start_year = selected_year_previous
    end_year = selected_year_current

    # Pivot data to have Year as index and State as columns
    enrollment_pivot = enrollment_df.pivot(index='Year', columns='State', values='Enrollment')

    # Set title based on department
    sources = ['mainecare_enrollment', 'nh_medicaid_enrollment'] if department == 'HEALTH & HUMAN SERVICES' else ['me_public_school_enrollment', 'nh_public_school_enrollment']
    source_superscripts = SourcesConfig.get_footnotes_superscripts(sources)
    title = f'{"Medicaid" if department == "HEALTH & HUMAN SERVICES" else "Public School"} Enrollment Comparison: Maine vs New Hampshire{source_superscripts}'

    fig = go.Figure()

    # Maine enrollment trace
    fig.add_trace(go.Scatter(
        x=enrollment_pivot.index,
        y=enrollment_pivot['Maine'],
        mode='lines',
        name='Maine',
        line=dict(color='blue')
    ))

    # New Hampshire enrollment trace
    fig.add_trace(go.Scatter(
        x=enrollment_pivot.index,
        y=enrollment_pivot['New Hampshire'],
        mode='lines',
        name='New Hampshire',
        line=dict(color='red')
    ))

    fig.update_layout(
        title=title,
        xaxis_title='Fiscal Year',
        yaxis_title='Enrollment',
        xaxis=dict(
            range=[start_year, end_year],
            autorange=False,
            tickangle=-45
        ),
        yaxis=dict(rangemode='tozero')
    )

    return fig


def plot_budget_per_enrollee_comparison(data, department):
    """
    Create a line chart comparing Maine and New Hampshire budget per enrollee over time.

    Parameters:
    - data: BudgetAnalysisData object containing enrollment_df, me_standardized_df, and nh_standardized_df
    - department: The enrollment department ('HEALTH & HUMAN SERVICES' or 'EDUCATION')
    - funding_source: The funding source to use for budget calculation (default: 'DEPARTMENT TOTAL')

    Returns:
    - plotly.graph_objects.Figure: The plotly figure
    """

    # Extract data to local variables
    enrollment_df = data.enrollment_df[data.enrollment_df['Department'] == department]
    me_standardized_df = data.me_standardized_df
    nh_standardized_df = data.nh_standardized_df
    selected_year_current = data.selected_year_current
    selected_year_previous = data.selected_year_previous
    funding_source = 'DEPARTMENT TOTAL' # Don't have breakout yet for NH

    # Set start and end years based on data selection
    start_year = selected_year_previous
    end_year = selected_year_current

    # Get Maine enrollment data
    maine_enrollment = enrollment_df[enrollment_df['State'] == 'Maine'].set_index('Year')['Enrollment']
    nh_enrollment = enrollment_df[enrollment_df['State'] == 'New Hampshire'].set_index('Year')['Enrollment']

    # Get Maine department budget data
    me_budget = me_standardized_df.loc[(department, funding_source)]

    # Get New Hampshire equivalent department budget data
    nh_budget = nh_standardized_df.loc[(department, funding_source)]

    # Calculate budget per enrollee for both states
    me_budget_per_enrollee = (me_budget / maine_enrollment).round(0)
    nh_budget_per_enrollee = (nh_budget / nh_enrollment).round(0)

    # Set title based on department
    dept_short = 'HHS' if department == 'HEALTH & HUMAN SERVICES' else department.title()
    program_name = 'Medicaid Enrollee' if department == 'HEALTH & HUMAN SERVICES' else 'Student'

    fig = go.Figure()

    # Maine budget per enrollee trace
    fig.add_trace(go.Scatter(
        x=me_budget_per_enrollee.index,
        y=me_budget_per_enrollee.values,
        mode='lines',
        name='Maine',
        line=dict(color='blue')
    ))

    # New Hampshire budget per enrollee trace
    fig.add_trace(go.Scatter(
        x=nh_budget_per_enrollee.index,
        y=nh_budget_per_enrollee.values,
        mode='lines',
        name='New Hampshire',
        line=dict(color='red')
    ))

    sources = ['mainecare_', 'transparent_nh_expenditure']

    sources = (['mainecare_enrollment', 'nh_medicaid_enrollment'] if department == 'HEALTH & HUMAN SERVICES' else ['me_public_school_enrollment', 'nh_public_school_enrollment']) + ['maine_legislature', 'transparent_nh_expenditure']
    source_superscripts = SourcesConfig.get_footnotes_superscripts(sources)
    title = f'{dept_short} Budget per {program_name} Comparison - {funding_source.title()}{source_superscripts}'

    fig.update_layout(
        title=title,
        xaxis_title='Fiscal Year',
        yaxis_title=f'Budget per {program_name} ($)',
        xaxis=dict(
            range=[start_year, end_year],
            autorange=False,
            tickangle=-45
        ),
        yaxis=dict(rangemode='tozero')
    )

    return fig


def plot_headline_comparison(data, start_year, end_year):
    """
    Create a line chart comparing Maine and New Hampshire GDP and Total Spending over time.

    Parameters:
    - data: BudgetAnalysisData object containing raw_economic_df, me_standardized_df, nh_standardized_df
    - start_year: Starting year for the comparison (str)
    - end_year: Ending year for the comparison (str)

    Returns:
    - plotly.graph_objects.Figure: The plotly figure
    """

    # Extract raw GDP data directly (GDP data is in millions of dollars from FRED)
    me_gdp = data.raw_economic_df.loc['Maine GDP']
    nh_gdp = data.raw_economic_df.loc['New Hampshire GDP']

    # Scale to billions for display (divide by 1e3 since GDP is in millions: millions / 1e3 = billions)
    me_gdp_scaled = me_gdp / 1e3
    nh_gdp_scaled = nh_gdp / 1e3

    # Extract total spending data
    me_spending = data.me_standardized_df.loc[('TOTAL', 'DEPARTMENT TOTAL')] / Config.TOTAL_BUDGET_SCALE
    nh_spending = data.nh_standardized_df.loc[('TOTAL', 'DEPARTMENT TOTAL')] / Config.TOTAL_BUDGET_SCALE

    fig = go.Figure()

    # Maine spending trace (left axis, blue)
    fig.add_trace(go.Scatter(
        x=me_spending.index,
        y=me_spending.values,
        mode='lines',
        name='Maine Total Appropriations',
        line=dict(color='blue')
    ))

    # NH spending trace (left axis, red)
    fig.add_trace(go.Scatter(
        x=nh_spending.index,
        y=nh_spending.values,
        mode='lines',
        name='NH Total Appropriations',
        line=dict(color='red')
    ))

    # Maine GDP trace (right axis, light blue)
    fig.add_trace(go.Scatter(
        x=me_gdp_scaled.index,
        y=me_gdp_scaled.values,
        mode='lines',
        name='Maine GDP',
        line=dict(color='lightblue', dash='dash'),
        yaxis='y2'
    ))

    # New Hampshire GDP trace (right axis, light red)
    fig.add_trace(go.Scatter(
        x=nh_gdp_scaled.index,
        y=nh_gdp_scaled.values,
        mode='lines',
        name='NH GDP',
        line=dict(color='lightcoral', dash='dash'),
        yaxis='y2'
    ))

    sources = ['FRED_me_gdp', 'FRED_nh_gdp', 'maine_legislature', 'transparent_nh_expenditure']
    source_superscripts = SourcesConfig.get_footnotes_superscripts(sources)

    fig.update_layout(
        title=f'ME vs NH Headline Comparison{source_superscripts}',
        xaxis_title='Year',
        yaxis_title=f'Total Appropriations ({Config.TOTAL_BUDGET_SCALE_LABEL})',
        yaxis2=dict(
            title=f'GDP ({Config.TOTAL_BUDGET_SCALE_LABEL})',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        xaxis=dict(
            range=[start_year, end_year],
            autorange=False,
            tickangle=-45
        ),
        yaxis=dict(rangemode='tozero'),
        legend=dict(x=1.05, y=1)
    )

    return fig
