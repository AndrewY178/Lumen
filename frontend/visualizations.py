"""Visualization functions for Potion Flow Monitoring Dashboard"""
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def plot_cauldron_map(df_cauldrons, market_data, df_overflow, network_data, df_levels, df_fill_rates):
    """Create network map visualization with cauldrons, levels, and market.
    
    Args:
        df_cauldrons: DataFrame with cauldron information
        market_data: Dictionary with market information
        df_overflow: DataFrame with overflow risk analysis
        network_data: Dictionary with network graph data
        df_levels: DataFrame with cauldron level data
        df_fill_rates: DataFrame with fill rates
        
    Returns:
        Plotly figure object
    """
    fig = go.Figure()
    
    # Build node position mapping
    cauldrons_list = df_cauldrons.reset_index()
    node_positions = {}
    for _, cauldron in cauldrons_list.iterrows():
        node_positions[cauldron['id']] = (cauldron['longitude'], cauldron['latitude'])
    
    market_lat = market_data.get('latitude', 33.2145)
    market_lon = market_data.get('longitude', -97.133)
    market_id = market_data.get('id', 'market')
    node_positions[market_id] = (market_lon, market_lat)
    
    # Draw edges first (behind nodes)
    edges = network_data.get('edges', [])
    for edge in edges:
        from_node = edge.get('from')
        to_node = edge.get('to')
        
        if from_node in node_positions and to_node in node_positions:
            x0, y0 = node_positions[from_node]
            x1, y1 = node_positions[to_node]
            
            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode='lines',
                line=dict(color='lightgray', width=1),
                opacity=0.5,
                hoverinfo='skip',
                showlegend=False
            ))
    
    # Prepare cauldron data with levels and metrics
    cauldron_data = []
    marker_sizes = []
    risk_colors = []
    
    for _, cauldron in cauldrons_list.iterrows():
        cauldron_id = cauldron['id']
        
        # Get current level
        cauldron_col = f'cauldron_levels.{cauldron_id}'
        current_level = np.nan
        if cauldron_col in df_levels.columns:
            level_series = df_levels[cauldron_col].dropna()
            if len(level_series) > 0:
                current_level = level_series.iloc[-1]
        
        # Get overflow data
        overflow_row = df_overflow[df_overflow['cauldron_id'] == cauldron_id]
        max_volume = cauldron.get('max_volume', np.nan)
        utilization_pct = np.nan
        hours_to_overflow = np.nan
        risk_level = 'UNKNOWN'
        fill_rate = np.nan
        
        if len(overflow_row) > 0:
            risk_level = overflow_row.iloc[0]['risk_level']
            utilization_pct = overflow_row.iloc[0]['utilization_pct']
            hours_to_overflow = overflow_row.iloc[0]['hours_to_overflow']
            max_volume = overflow_row.iloc[0]['max_volume']
        
        # Get fill rate
        fill_rate_row = df_fill_rates[df_fill_rates['cauldron'] == cauldron_col]
        if len(fill_rate_row) > 0:
            fill_rate = fill_rate_row.iloc[0]['fill_rate_per_hour']
        
        # Color by risk level
        if risk_level == 'HIGH':
            risk_colors.append('red')
        elif risk_level == 'MEDIUM':
            risk_colors.append('orange')
        elif risk_level == 'LOW':
            risk_colors.append('green')
        else:
            risk_colors.append('blue')
        
        # Marker size proportional to utilization (10-30 range)
        if not np.isnan(utilization_pct):
            marker_size = 10 + (utilization_pct / 100) * 20
        else:
            marker_size = 15
        marker_sizes.append(marker_size)
        
        # Prepare hover data (use 0 for missing numeric values to avoid formatting issues)
        cauldron_data.append({
            'id': cauldron_id,
            'name': cauldron.get('name', 'N/A'),
            'current_level': current_level if not np.isnan(current_level) else 0,
            'max_volume': max_volume if not np.isnan(max_volume) else 0,
            'utilization_pct': utilization_pct if not np.isnan(utilization_pct) else 0,
            'hours_to_overflow': hours_to_overflow if not np.isnan(hours_to_overflow) else 0,
            'fill_rate': fill_rate if not np.isnan(fill_rate) else 0,
            'risk_level': risk_level,
            'has_level': not np.isnan(current_level),
            'has_max': not np.isnan(max_volume),
            'has_util': not np.isnan(utilization_pct),
            'has_hours': not np.isnan(hours_to_overflow),
            'has_fill': not np.isnan(fill_rate)
        })
    
    # Add cauldrons with level labels
    level_labels = []
    for cd in cauldron_data:
        if cd['has_level'] and cd['current_level'] > 0:
            level_labels.append(f"{cd['current_level']:.0f}L")
        else:
            level_labels.append("")
    
    # Create hover text with proper handling of missing values
    hover_texts = []
    for cd in cauldron_data:
        level_str = f"{cd['current_level']:.1f}L" if cd['has_level'] else "N/A"
        max_str = f"{cd['max_volume']:.0f}L" if cd['has_max'] else "N/A"
        util_str = f"{cd['utilization_pct']:.1f}%" if cd['has_util'] else "N/A"
        hours_str = f"{cd['hours_to_overflow']:.1f}h" if cd['has_hours'] else "N/A"
        fill_str = f"{cd['fill_rate']:.2f} L/h" if cd['has_fill'] else "N/A"
        
        hover_texts.append(
            f"<b>{cd['id']}</b><br>"
            f"{cd['name']}<br>"
            f"Level: {level_str} / {max_str}<br>"
            f"Utilization: {util_str}<br>"
            f"Hours to Overflow: {hours_str}<br>"
            f"Fill Rate: {fill_str}<br>"
            f"Risk: {cd['risk_level']}"
        )
    
    fig.add_trace(go.Scatter(
        x=cauldrons_list['longitude'],
        y=cauldrons_list['latitude'],
        mode='markers+text',
        marker=dict(
            size=marker_sizes,
            color=risk_colors,
            line=dict(width=2, color='white'),
            opacity=0.8
        ),
        text=cauldrons_list['id'].str.replace('cauldron_', ''),
        textposition="top center",
        textfont=dict(size=9, color='black'),
        name='Cauldrons',
        customdata=hover_texts,
        hovertemplate='%{customdata}<extra></extra>'
    ))
    
    # Add level labels below cauldron IDs
    fig.add_trace(go.Scatter(
        x=cauldrons_list['longitude'],
        y=cauldrons_list['latitude'] - 0.0005,  # Slightly below the marker
        mode='text',
        text=level_labels,
        textposition="top center",
        textfont=dict(size=8, color='darkblue'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Add market
    fig.add_trace(go.Scatter(
        x=[market_lon],
        y=[market_lat],
        mode='markers+text',
        marker=dict(size=30, color='#FF6B6B', symbol='hexagon', line=dict(width=2, color='white')),
        text='🍄',
        textposition="middle center",
        textfont=dict(size=20),
        name='Market',
        hovertemplate='<b>Enchanted Market</b><br>Sales Point<extra></extra>'
    ))
    
    fig.update_layout(
        title="Potion Factory Network Map - All Cauldrons, Levels & Sales Point",
        xaxis=dict(
            title="Longitude",
            showgrid=False,
            zeroline=False,
            scaleanchor="y",
            scaleratio=1
        ),
        yaxis=dict(
            title="Latitude",
            showgrid=False,
            zeroline=False
        ),
        height=600,
        hovermode='closest',
        showlegend=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def plot_level_timeseries(df_levels, cauldron_id):
    """Plot time series of cauldron level over time.
    
    Args:
        df_levels: DataFrame with cauldron level data
        cauldron_id: ID of the cauldron to plot
        
    Returns:
        Plotly figure object
    """
    col = f'cauldron_levels.{cauldron_id}'
    data = df_levels[col].dropna()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        mode='lines',
        name='Level',
        line=dict(color='blue', width=1)
    ))
    
    fig.update_layout(
        title=f"{cauldron_id} - Level Over Time",
        xaxis_title="Time",
        yaxis_title="Level (liters)",
        height=350,
        hovermode='x unified'
    )
    
    return fig


def plot_rate_of_change(df_levels, cauldron_id, fill_rate):
    """Plot rate of change for cauldron level over time.
    
    Args:
        df_levels: DataFrame with cauldron level data
        cauldron_id: ID of the cauldron to plot
        fill_rate: Fill rate for reference line
        
    Returns:
        Plotly figure object
    """
    col = f'cauldron_levels.{cauldron_id}'
    series = df_levels[col].dropna()
    
    time_diffs = series.index.to_series().diff().dt.total_seconds() / 60
    level_diffs = series.diff()
    rates = level_diffs / time_diffs
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rates.index,
        y=rates.values,
        mode='lines',
        name='Rate',
        line=dict(color='orange', width=1)
    ))
    
    # Add median line
    median_rate = rates.median()
    fig.add_hline(y=median_rate, line_dash="dash", line_color="green",
                  annotation_text=f"Median: {median_rate:.4f} L/min")
    fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.5)
    
    fig.update_layout(
        title=f"{cauldron_id} - Rate of Change Over Time",
        xaxis_title="Time",
        yaxis_title="Rate (L/min)",
        height=350,
        hovermode='x unified'
    )
    
    return fig

