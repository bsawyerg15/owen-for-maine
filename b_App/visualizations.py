import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

plt.style.use('default')

def plot_funding_sources(ax, funding_source, input_df, fred_client, name='', start_year='2016'):
    """Create funding source chart with economic indicators."""
    # Prepare dataframes
    fund_df = input_df.xs(funding_source, level='Funding Source').fillna(0)
    df = fund_df[fund_df.index != 'GRAND TOTALS - ALL DEPARTMENTS']
    df = df.sort_values(by=df.columns[-1], ascending=False) / 1e9

    # Get economic indicators
    total_funding_name = 'GRAND TOTALS - ALL DEPARTMENTS' if funding_source == 'DEPARTMENT TOTAL' else funding_source
    try:
        grand_total_start = input_df.loc[('GRAND TOTALS - ALL DEPARTMENTS', total_funding_name), start_year] / 1e9
        start_value = grand_total_start if grand_total_start > 0 else 8.2
    except KeyError:
        start_value = 8.2

    try:
        from data_ingestion import get_indexed_fred_series
        cpi_yearly_reindexed = get_indexed_fred_series(fred_client, 'CPIAUCSL', start_year, start_value)
        maine_gdp_reindexed = get_indexed_fred_series(fred_client, 'MENQGSP', start_year, start_value)
        population = get_indexed_fred_series(fred_client, 'MEPOP', start_year, start_value)
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
    ax.set_ylabel('Budget (Billions of $)')

    return df

def plot_department_breakdown(ax, department, me_as_reported_df, fred_client, start_year='2016'):
    """Create department breakdown chart by funding source."""
    department_df = me_as_reported_df.xs(department, level='Department').fillna(0)
    df = department_df[department_df.index != 'DEPARTMENT TOTAL']
    df = df.sort_values(by=df.columns[-1], ascending=False) / 1e6

    # Get economic indicators
    try:
        grand_total_start = me_as_reported_df.loc[('GRAND TOTALS - ALL DEPARTMENTS', 'DEPARTMENT TOTAL'), start_year] / 1e9
        start_value = grand_total_start if grand_total_start > 0 else 8.2
    except KeyError:
        start_value = 8.2

    try:
        from data_ingestion import get_indexed_fred_series
        cpi_yearly_reindexed = get_indexed_fred_series(fred_client, 'CPIAUCSL', start_year, start_value)
        maine_gdp_reindexed = get_indexed_fred_series(fred_client, 'MENQGSP', start_year, start_value)
        population = get_indexed_fred_series(fred_client, 'MEPOP', start_year, start_value)
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

    ax.set_title(f'{department} Spending by Funding Source (in Millions)')
    ax.set_xlabel('Fiscal Year')
    ax.set_ylabel('Budget (Millions of $)')

    return df

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
        name='y=x',
        line=dict(color='gray', dash='dash')
    ))

    fig.update_layout(
        width=600,
        height=600,
        title=f'Maine vs New Hampshire State Budgets',
        xaxis_title='Maine Budget (Million $)',
        yaxis_title='New Hampshire Budget (Million $)'
    )

    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    fig.show()

    return fig

def plot_small_departments_summary(ex_big_total_df):
    """Create summary plot for departments excluding major ones."""
    mean_small = ex_big_total_df.mean() / 1e6
    count_small = (ex_big_total_df > 0).sum()

    fig, ax = plt.subplots(figsize=(8, 3))
    ax2 = ax.twinx()

    ax.plot(mean_small, label='Mean Size ($mm)')
    ax2.plot(count_small, color='orange', label='Count (Right)')

    ax.set_title('Departments ex Health, Education, and Transportation')

    fig.legend(loc='right', fontsize=8)

    return fig, ax, ax2
