import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from b_App.data_ingestion import get_fred_series
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


def plot_budget_and_spending(df, department='TOTAL', start_year='2016'):
    
    df = (df / Config.TOTAL_BUDGET_SCALE).round(Config.TOTAL_BUDGET_SCALE_ROUNDING)
    
    spending_name = 'DEPARTMENT TOTAL'
    budget_name = 'DEPARTMENT TOTAL ex FEDERAL'

    spending = df.loc[(department, spending_name)]
    budget = df.loc[(department, budget_name)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=spending.index,
        y=spending.values,
        mode='lines',
        name='Spending',
        line=dict(color='blue')
    ))
    fig.add_trace(go.Scatter(
        x=budget.index,
        y=budget.values,
        mode='lines',
        name='o.w. State Funded',
        line=dict(color='red')
    ))

    fig.update_yaxes(title_text=Config.TOTAL_BUDGET_SCALE_LABEL, rangemode='tozero')
    fig.update_xaxes(tickangle=-45)
    fig.update_layout(
        title='Maine State Budget and Spending'
    )

    return fig


def plot_funding_sources(ax, funding_source, input_df, fred_client, name='', start_year='2016'):
    """Create funding source chart with economic indicators."""
    # Prepare dataframes
    fund_df = input_df.xs(funding_source, level='Funding Source').fillna(0)
    df = fund_df[fund_df.index != 'GRAND TOTALS - ALL DEPARTMENTS']
    df = df.sort_values(by=df.columns[-1], ascending=False) / Config.TOTAL_BUDGET_SCALE

    # Get economic indicators
    total_funding_name = 'GRAND TOTALS - ALL DEPARTMENTS' if funding_source == 'DEPARTMENT TOTAL' else funding_source
    try:
        grand_total_start = input_df.loc[('GRAND TOTALS - ALL DEPARTMENTS', total_funding_name), start_year] / Config.TOTAL_BUDGET_SCALE
        start_value = grand_total_start if grand_total_start > 0 else 8.2
    except KeyError:
        start_value = 8.2

    try:
        from data_ingestion import get_fred_series
        cpi_yearly_reindexed = get_fred_series(fred_client, 'CPIAUCSL', start_year, start_value)
        maine_gdp_reindexed = get_fred_series(fred_client, 'MENQGSP', start_year, start_value)
        population = get_fred_series(fred_client, 'MEPOP', start_year, start_value)
        add_economic_indicators = True
    except Exception as e:
        print(f"Warning: Could not fetch FRED data: {e}")
        # Create dummy series for plotting
        years = df.columns
        cpi_yearly_reindexed = pd.Series([start_value] * len(years), index=years)
        maine_gdp_reindexed = pd.Series([start_value] * len(years), index=years)
        population = pd.Series([start_value] * len(years), index=years)
        add_economic_indicators = False

    # Plotting
    if df.empty or df.shape[0] == 0:
        ax.text(0.5, 0.5, 'No data available', transform=ax.transAxes, ha='center', va='center')
        return df

    top_5 = df.iloc[:5].index
    ax.stackplot(df.columns, df.values, labels=top_5)

    ax.plot(cpi_yearly_reindexed.index, cpi_yearly_reindexed.values, color='black', linestyle='--', label='CPI (Re-Indexed)')
    ax.plot(maine_gdp_reindexed.index, maine_gdp_reindexed.values, color='Blue', linestyle='--', label='Maine GDP (Re-Indexed)')
    ax.plot(population.index, population.values, color='RED', linestyle='--', label='Maine Res. Population')

    # Chart features
    ax.grid(axis='y', alpha=0.5, linestyle='dotted')
    ax.legend(loc='upper left', fontsize='8')

    if name:
        budget_name = name
    elif funding_source == "DEPARTMENT TOTAL":
        budget_name = 'State Budget'
    else:
        budget_name = funding_source

    ax.set_title(f'Maine {budget_name} by Department (in Billions)')
    ax.set_xlabel('Fiscal Year')
    ax.set_ylabel(f'Budget ({Config.TOTAL_BUDGET_SCALE_LABEL})')

    return df


def plot_department_funding_sources(ax, department, me_as_reported_df, start_year='2016'):
    """Create department breakdown chart by funding source."""
    department_df = me_as_reported_df.xs(department, level='Department').fillna(0)
    funding_sources_to_exclude = ['DEPARTMENT TOTAL ex FEDERAL', 'DEPARTMENT TOTAL', 'GRAND TOTALS - ALL DEPARTMENTS']
    df = department_df[~department_df.index.isin(funding_sources_to_exclude)]
    df = df.sort_values(by=df.columns[-1], ascending=False) / Config.DEPARTMENT_SCALE

    top_5 = df.iloc[:5].index
    ax.stackplot(df.columns, df.values, labels=top_5)

    # Chart features
    ax.grid(axis='y', alpha=0.5, linestyle='dotted')
    ax.legend(loc='upper left', fontsize='8')

    ax.set_title(f'{department} Spending by Funding Source (in Millions)')
    ax.set_xlabel('Fiscal Year')
    ax.set_ylabel(f'Budget ({Config.DEPARTMENT_SCALE_LABEL})')

    return df


def plot_spending_vs_econ_index(spending_series, econ_index_df, to_hide=[]):
    """Create a plotly chart plotting spending series vs each economic index, with first points aligned."""
    
    spending_series = spending_series / Config.TOTAL_BUDGET_SCALE

    # Determine the first year from the minimum of both series indices/columns
    first_year = str(min([int(y) for y in spending_series.index]))

    # Get base value from spending series at first year
    base_value = spending_series.loc[first_year]

    # Re-index economic indices to start at base_value
    econ_reindexed = econ_index_df.div(econ_index_df[first_year], axis=0) * base_value

    # Create plotly figure
    fig = go.Figure()

    # Add spending series trace
    fig.add_trace(go.Scatter(
        x=spending_series.index,
        y=spending_series.values,
        mode='lines',
        name='Spending',
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

    # Update layout
    fig.update_layout(
        title='Spending vs Economic Indices',
        xaxis_title='Year',
        yaxis_title='Value',
        legend_title='Legend',
    )
    fig.update_yaxes(title_text=Config.TOTAL_BUDGET_SCALE_LABEL)

    return fig


def plot_state_comparison(comparison_df_current, comparison_df_previous, year_current, year_previous):
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


def plot_small_departments_summary(df, big_departments=['DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)', 'DEPARTMENT OF EDUCATION', 'DEPARTMENT OF TRANSPORTATION']):
    """Create summary plot for departments excluding major ones."""
    total_df = df.xs('DEPARTMENT TOTAL', level='Funding Source').fillna(0) / Config.DEPARTMENT_SCALE
    ex_big_total_df = total_df[~total_df.index.isin(big_departments)]
    ex_big_total_df = ex_big_total_df.replace(0, np.nan)
    mean_small = ex_big_total_df.mean()
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
        title='Summary of Departments ex Health, Education, and Transportation',
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


def produce_department_bar_chart(df, year, top_n=10, to_exclude=['TOTAL'], produce_all_others=False, prior_year=None, title=None):
    """Produce bar chart of top N departments by spending for a given year."""
    total_df = df.xs('DEPARTMENT TOTAL', level='Funding Source').fillna(0) / Config.DEPARTMENT_SCALE
    total_df = total_df.round(Config.DEPARTMENT_SCALE_ROUNDING)
    years_to_use = [year, prior_year] if prior_year else [year]
    total_for_year_df = total_df[years_to_use].sort_values(by=year, ascending=False)
    total_with_exclusions = total_for_year_df[~total_for_year_df.index.isin(to_exclude)]
    top_departments = total_with_exclusions.head(top_n)
    if produce_all_others:
        others_sum = total_with_exclusions.iloc[top_n:].sum()
        top_departments = pd.concat([top_departments, pd.DataFrame([others_sum.values], index=['ALL OTHERS'], columns=top_departments.columns)])

    # Create vertical bar chart using plotly.graph_objects for better control over multiline labels
    fig = go.Figure()

    if prior_year:
        fig.add_trace(go.Bar(
            x=list(range(len(top_departments))),
            y=top_departments[prior_year].values,
            marker_color='lightblue',
            name=f'{prior_year}'
        ))

    fig.add_trace(go.Bar(
        x=list(range(len(top_departments))),
        y=top_departments[year].values,
        text=[f'{val}' for val in top_departments[year].values],
        textposition='auto',
        hovertext=top_departments.index,
        marker_color='blue',
        name=f'{year}'
    ))

    # Set x-axis labels with multiline text
    multiline_labels = [clean_department_labels(department) for department in top_departments.index]
    fig.update_xaxes(
        tickmode='array',
        tickvals=list(range(len(top_departments))),
        ticktext=multiline_labels,
        tickangle=-45
    )

    if not title:
        title = f'Departments by Spending'

    fig.update_yaxes(title_text=f'Spending ({Config.DEPARTMENT_SCALE_LABEL})')
    fig.update_layout(
        title=title,
        xaxis_title='Department',
        showlegend=True,
        height=500,
        barmode='stack'
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
