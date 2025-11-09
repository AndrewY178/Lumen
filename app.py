import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from api_client import APIClient
from data_processor import DataProcessor
from drain_detector import DrainDetector
from ticket_matcher import TicketMatcher
from analytics import Analytics

st.set_page_config(page_title="🧙 Potion Flow Monitor", layout="wide")

@st.cache_data
def load_data():
    api_client = APIClient(cache_enabled=True)
    raw_data = api_client.fetch_all_data()
    
    processor = DataProcessor()
    df_levels = processor.transform_level_data(raw_data['level_data'])
    df_tickets = processor.transform_tickets(raw_data['tickets'])
    df_cauldrons = processor.transform_cauldrons(raw_data['cauldrons'])
    df_fill_rates = processor.calculate_fill_rates(df_levels)
    
    fill_rates = dict(zip(df_fill_rates['cauldron'], df_fill_rates['fill_rate_per_min']))
    cauldron_ids = processor.get_cauldron_ids(df_levels)
    travel_times = api_client.fetch_travel_times(cauldron_ids)
    
    detector = DrainDetector()
    df_drain_events = detector.detect_all_drains(df_levels, fill_rates, travel_times)
    
    matcher = TicketMatcher()
    df_matched = matcher.match_drains_to_tickets(df_drain_events, df_tickets)
    
    analytics = Analytics()
    df_overflow = analytics.calculate_overflow_risk(df_levels, df_cauldrons, df_fill_rates)
    
    market_data = raw_data['market']
    
    return {
        'levels': df_levels,
        'tickets': df_tickets,
        'cauldrons': df_cauldrons,
        'drain_events': df_drain_events,
        'matched': df_matched,
        'fill_rates': df_fill_rates,
        'overflow': df_overflow,
        'market': market_data
    }

def plot_cauldron_map(df_cauldrons, market_data, df_overflow):
    fig = go.Figure()
    
    # Add cauldrons
    cauldrons_list = df_cauldrons.reset_index()
    colors = cauldrons_list.index.map(
        lambda x: f"cauldron_{x:03d}" if x < len(cauldrons_list) else "cauldron_000"
    )
    
    # Color by risk level
    risk_colors = []
    for _, cauldron in cauldrons_list.iterrows():
        cauldron_id = cauldron['id']
        overflow_row = df_overflow[df_overflow['cauldron_id'] == cauldron_id]
        if len(overflow_row) > 0:
            risk = overflow_row.iloc[0]['risk_level']
            if risk == 'HIGH':
                risk_colors.append('red')
            elif risk == 'MEDIUM':
                risk_colors.append('orange')
            else:
                risk_colors.append('green')
        else:
            risk_colors.append('blue')
    
    fig.add_trace(go.Scatter(
        x=cauldrons_list['longitude'],
        y=cauldrons_list['latitude'],
        mode='markers+text',
        marker=dict(size=20, color=risk_colors, line=dict(width=2, color='white')),
        text=cauldrons_list['id'],
        textposition="top center",
        textfont=dict(size=10),
        name='Cauldrons',
        customdata=cauldrons_list[['id', 'name', 'max_volume']],
        hovertemplate='<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Max: %{customdata[2]}L<extra></extra>'
    ))
    
    # Add market
    market_lat = market_data.get('latitude', 33.2145)
    market_lon = market_data.get('longitude', -97.133)
    fig.add_trace(go.Scatter(
        x=[market_lon],
        y=[market_lat],
        mode='markers+text',
        marker=dict(size=30, color='gold', symbol='star', line=dict(width=2, color='black')),
        text=['Market'],
        textposition="top center",
        textfont=dict(size=12, color='black'),
        name='Market',
        hovertemplate='<b>Enchanted Market</b><extra></extra>'
    ))
    
    fig.update_layout(
        title="Potion Factory Network Map (Click cauldron to view details)",
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        height=600,
        hovermode='closest',
        showlegend=True
    )
    
    return fig

def plot_level_timeseries(df_levels, cauldron_id):
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

# Main App
st.title("🧙 Potion Flow Monitoring Dashboard")

with st.spinner("Loading data from API..."):
    data = load_data()

df_levels = data['levels']
df_cauldrons = data['cauldrons']
df_overflow = data['overflow']
df_fill_rates = data['fill_rates']
market_data = data['market']

# Sidebar stats
st.sidebar.header("System Status")
st.sidebar.metric("Total Cauldrons", len(df_cauldrons))
st.sidebar.metric("Data Points", len(df_levels))
st.sidebar.metric("High Risk Cauldrons", len(df_overflow[df_overflow['risk_level'] == 'HIGH']))

if len(data['matched']) > 0:
    summary = TicketMatcher.get_summary(data['matched'])
    st.sidebar.metric("Matching Accuracy", f"{summary['accuracy_pct']:.1f}%")
    st.sidebar.metric("Unaccounted Volume", f"{summary['total_unaccounted']:.0f}L")

# Map
st.subheader("🗺️ Cauldron Network Map")
map_fig = plot_cauldron_map(df_cauldrons, market_data, df_overflow)
st.plotly_chart(map_fig, use_container_width=True)

# Cauldron selector
st.subheader("📊 Cauldron Analysis")
cauldron_ids = [col.replace('cauldron_levels.', '') for col in df_levels.columns if 'cauldron' in col.lower()]
selected_cauldron = st.selectbox("Select a cauldron to view details:", cauldron_ids)

if selected_cauldron:
    col1, col2, col3 = st.columns(3)
    
    # Get cauldron info
    cauldron_info = df_cauldrons.loc[selected_cauldron] if selected_cauldron in df_cauldrons.index else None
    overflow_info = df_overflow[df_overflow['cauldron_id'] == selected_cauldron]
    fill_rate_info = df_fill_rates[df_fill_rates['cauldron'].str.contains(selected_cauldron)]
    
    if cauldron_info is not None:
        col1.metric("Name", cauldron_info.get('name', 'N/A'))
        col2.metric("Max Volume", f"{cauldron_info.get('max_volume', 0)}L")
    
    if len(overflow_info) > 0:
        col3.metric("Current Level", f"{overflow_info.iloc[0]['current_level']:.1f}L")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Utilization", f"{overflow_info.iloc[0]['utilization_pct']:.1f}%")
        col2.metric("Hours to Overflow", f"{overflow_info.iloc[0]['hours_to_overflow']:.1f}h")
        risk_color = {
            'HIGH': '🔴',
            'MEDIUM': '🟡',
            'LOW': '🟢'
        }.get(overflow_info.iloc[0]['risk_level'], '⚪')
        col3.metric("Risk Level", f"{risk_color} {overflow_info.iloc[0]['risk_level']}")
    
    if len(fill_rate_info) > 0:
        st.metric("Fill Rate", f"{fill_rate_info.iloc[0]['fill_rate_per_hour']:.2f} L/hour")
    
    # Plots
    st.markdown("---")
    level_fig = plot_level_timeseries(df_levels, selected_cauldron)
    st.plotly_chart(level_fig, use_container_width=True)
    
    fill_rate = fill_rate_info.iloc[0]['fill_rate_per_min'] if len(fill_rate_info) > 0 else 0.05
    rate_fig = plot_rate_of_change(df_levels, selected_cauldron, fill_rate)
    st.plotly_chart(rate_fig, use_container_width=True)
    
    # Drain events for this cauldron
    cauldron_drains = data['drain_events'][data['drain_events']['cauldron_id'] == selected_cauldron]
    if len(cauldron_drains) > 0:
        st.subheader(f"💧 Drain Events ({len(cauldron_drains)})")
        st.dataframe(
            cauldron_drains[['end_time', 'total_collected', 'drain_duration_min']].rename(columns={
                'end_time': 'Time',
                'total_collected': 'Volume (L)',
                'drain_duration_min': 'Duration (min)'
            }),
            use_container_width=True
        )

