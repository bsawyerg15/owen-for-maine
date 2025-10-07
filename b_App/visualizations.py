import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from b_App.data_ingestion import get_fred_series
from b_App.data_processing import create_state_comparison_through_time
from a_Configs.config import Config

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


def plot_department_funding_sources(department, me_as_reported_df, start_year='2016'):
    """Create department breakdown chart by funding source."""
    department_df = me_as_reported_df.xs(department, level='Department').fillna(0)
    funding_sources_to_exclude = ['DEPARTMENT TOTAL ex FEDERAL', 'DEPARTMENT TOTAL', 'GRAND TOTALS - ALL DEPARTMENTS']
    df = department_df[~department_df.index.isin(funding_sources_to_exclude)]
    df = df.sort_values(by=df.columns[-1], ascending=False)

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
        title=f'{department_name} Spending by Funding Source'.strip(),
        xaxis_title='Fiscal Year',
        yaxis_title=f'Budget ({department_scale_label})'
    )

    # Add grid lines
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='lightgray', gridwidth=1)

    return fig


def plot_spending_vs_econ_index(spending_series, econ_index_df, to_hide=[], funding_source='TOTAL', title=None):
    """Create a plotly chart plotting spending series vs each economic index, with first points aligned."""
    
    spending_series = (spending_series / Config.TOTAL_BUDGET_SCALE).round(Config.TOTAL_BUDGET_SCALE_ROUNDING)

    # Determine the first year from the minimum of both series indices/columns
    first_year = str(min([int(y) for y in spending_series.index]))

    # Get base value from spending series at first year
    base_value = spending_series.loc[first_year]

    # Re-index economic indices to start at base_value
    econ_reindexed = (econ_index_df.div(econ_index_df[first_year], axis=0) * base_value).round(Config.TOTAL_BUDGET_SCALE_ROUNDING)

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

    if not title:
        title = f'{funding_source.title()} Spending vs Economic Indices'

    # Update layout
    fig.update_layout(
        title=title,
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


def plot_state_comparison_bars(comparison_df_current, comparison_df_prior, year_current, year_prior, departments_to_show=None, title=None):
    """Create grouped bar chart comparing ME and NH budgets with prior year dots. If departments_to_show is provided, only those departments are shown in the specified order."""
    fig = go.Figure()

    # Scale values to department scale
    df = (comparison_df_current / Config.DEPARTMENT_SCALE).round(Config.DEPARTMENT_SCALE_ROUNDING)

    # Sort by ME budget descending (largest first)
    df = df.sort_values(by='ME', ascending=False)
    # Filter to specified departments if provided
    if departments_to_show is not None:
        df = df.loc[departments_to_show]

    # Scale and reindex prior year data to match sorted/limited current
    diff_df = comparison_df_current - comparison_df_prior
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
        name=f'ME {year_current}',
        marker_color='blue',
        text=[f'{val:.0f}' for val in df['ME'].values],
        textposition='auto'
    ))

    fig.add_trace(go.Bar(
        x=x_numeric,
        y=df['NH'],
        offset=0.2,
        width=0.4,
        name=f'NH {year_current}',
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
        name=f'ME Change from {year_prior}'
    ))

    fig.add_trace(go.Scatter(
        x=[i + 0.4 for i in x_numeric],  # centered on NH bars
        y=diff_df['NH'],
        mode='markers',
        marker=dict(symbol='diamond', color='lightcoral', size=8),
        name=f'NH Change from {year_prior}'
    ))

    # Adjust title based on filtering mode
    if not title:
        title = f'Maine vs New Hampshire State Budgets'

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


def plot_state_single_comparison_bars(comparison_df_current, comparison_df_prior, year_current, year_prior, department_name):
    """Create bar chart comparing ME and NH budgets for a single department with prior year dots."""
    if department_name not in comparison_df_current.index:
        raise ValueError(f"Department '{department_name}' not found in current data")

    fig = go.Figure()

    # Scale current and prior values
    current_me = (comparison_df_current.loc[department_name, 'ME'] / Config.DEPARTMENT_SCALE).round(Config.DEPARTMENT_SCALE_ROUNDING)
    current_nh = (comparison_df_current.loc[department_name, 'NH'] / Config.DEPARTMENT_SCALE).round(Config.DEPARTMENT_SCALE_ROUNDING)
    prior_me = (comparison_df_prior.loc[department_name, 'ME'] / Config.DEPARTMENT_SCALE).round(Config.DEPARTMENT_SCALE_ROUNDING)
    prior_nh = (comparison_df_prior.loc[department_name, 'NH'] / Config.DEPARTMENT_SCALE).round(Config.DEPARTMENT_SCALE_ROUNDING)

    # Calculate differences for prior year dots
    diff_me = current_me - prior_me
    diff_nh = current_nh - prior_nh

    # Add ME and NH current year bars
    fig.add_trace(go.Bar(
        x=['ME'],
        y=[current_me],
        name=f'ME {year_current}',
        marker_color='blue',
        text=[f'{current_me:.0f}'],
        textposition='auto'
    ))

    fig.add_trace(go.Bar(
        x=['NH'],
        y=[current_nh],
        name=f'NH {year_current}',
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
        name=f'ME Change from {year_prior}'
    ))

    fig.add_trace(go.Scatter(
        x=['NH'],
        y=[diff_nh],
        mode='markers',
        marker=dict(symbol='diamond', color='lightcoral', size=8),
        name=f'NH Change from {year_prior}'
    ))

    title = f'{department_name.title()}: Maine vs New Hampshire'

    fig.update_layout(
        title=title,
        yaxis_title=f'Budget ({Config.DEPARTMENT_SCALE_LABEL})'
    )

    return fig


def plot_small_departments_summary(df, funding_source='DEPARTMENT TOTAL', big_departments=['DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)', 'DEPARTMENT OF EDUCATION', 'DEPARTMENT OF TRANSPORTATION'], title='Summary of Departments ex Health, Education, and Transportation'):
    """Create summary plot for departments excluding major ones."""
    total_df = df.xs(funding_source, level='Funding Source').fillna(0)
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


def produce_department_bar_chart(df, year, top_n=10, funding_source='DEPARTMENT TOTAL', to_exclude=['TOTAL'], produce_all_others=False, prior_year=None, econ_index_df=None, title=None):
    """Produce bar chart of top N departments by spending for a given year."""
   
    # Select the departments and funding for the chart
    total_df = df.xs(funding_source, level='Funding Source').fillna(0) / Config.DEPARTMENT_SCALE
    total_df = total_df.round(Config.DEPARTMENT_SCALE_ROUNDING).astype(int)
    years_to_use = [year, prior_year] if prior_year else [year]
    total_for_year_df = total_df[years_to_use].sort_values(by=year, ascending=False)
    total_with_exclusions = total_for_year_df[~total_for_year_df.index.isin(to_exclude)]
    top_departments = total_with_exclusions.head(top_n)
    if produce_all_others:
        others_sum = total_with_exclusions.iloc[top_n:].sum()
        top_departments = pd.concat([top_departments, pd.DataFrame([others_sum.values], index=['ALL OTHERS'], columns=top_departments.columns)])

    # Generate CPI + inflation
    if prior_year and econ_index_df is not None:
        cpi_n_pop_growth_series = econ_index_df.loc['CPI & Population Growth']
        cpi_n_pop_growth = (cpi_n_pop_growth_series / cpi_n_pop_growth_series[prior_year]).dropna()
        
        # extend with growth rate if missing data
        if year in cpi_n_pop_growth.index:
            growth_over_period = cpi_n_pop_growth[year]
        else:
            latest_growth = cpi_n_pop_growth.tail(1)
            num_periods_avail = int(latest_growth.index[0]) - int(prior_year)
            num_periods = int(year) - int(prior_year)
            growth_over_period = (latest_growth.values[0] ** (num_periods / num_periods_avail))

        department_cpi_n_pop_growth = (top_departments[prior_year] * growth_over_period).round(Config.DEPARTMENT_SCALE_ROUNDING)


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

    if prior_year and econ_index_df is not None:
        fig.add_trace(go.Scatter(
            x=list(range(len(top_departments))),
            y=department_cpi_n_pop_growth.values,
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

    if not title:
        title = f'{funding_source.title()} Departments by Spending'

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
        if col[1] == '% Change':
            formats[col] = lambda x: '-' if pd.isna(x) else f'{x:.1f}%'
        else:
            formats[col] = lambda x: '-' if pd.isna(x) else f'{x:.0f}'
    styler = styler.format(formats)

    return styler
