import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import analysis

st.set_page_config(page_title="🧙 Potion Flow Monitor", layout="wide")

@st.cache_data
def load_data():
    raw_data = analysis.fetch_all_data()
    
    df_levels = analysis.transform_level_data(raw_data['level_data'])
    df_tickets = analysis.transform_tickets(raw_data['tickets'])
    df_cauldrons = analysis.transform_cauldrons(raw_data['cauldrons'])
    df_fill_rates = analysis.calculate_fill_rates(df_levels)
    
    fill_rates = dict(zip(df_fill_rates['cauldron'], df_fill_rates['fill_rate_per_min']))
    cauldron_ids = analysis.get_cauldron_ids(df_levels)
    travel_times = analysis.fetch_travel_times(cauldron_ids)
    
    df_drain_events = analysis.detect_all_drains(df_levels, fill_rates, travel_times)
    df_matched = analysis.match_drains_to_tickets(df_drain_events, df_tickets)
    df_overflow = analysis.calculate_overflow_risk(df_levels, df_cauldrons, df_fill_rates)
    
    df_reconciliation = analysis.get_daily_reconciliation(df_matched, df_tickets)
    df_witch_perf = analysis.get_witch_performance(df_matched, df_tickets)
    df_priority = analysis.get_overflow_priority(df_overflow, travel_times)
    patterns = analysis.get_suspicious_patterns(df_matched)
    
    couriers_data = raw_data['couriers']
    df_couriers = pd.DataFrame(couriers_data if isinstance(couriers_data, list) else [couriers_data])
    
    market_data = raw_data['market']
    network_data = raw_data['network']
    
    return {
        'levels': df_levels,
        'tickets': df_tickets,
        'cauldrons': df_cauldrons,
        'drain_events': df_drain_events,
        'matched': df_matched,
        'fill_rates': df_fill_rates,
        'overflow': df_overflow,
        'reconciliation': df_reconciliation,
        'witch_perf': df_witch_perf,
        'priority': df_priority,
        'patterns': patterns,
        'couriers': df_couriers,
        'market': market_data,
        'network': network_data,
        'travel_times': travel_times
    }

def plot_cauldron_map(df_cauldrons, market_data, df_overflow, network_data, df_levels, df_fill_rates):
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
df_reconciliation = data['reconciliation']
df_witch_perf = data['witch_perf']
df_priority = data['priority']
patterns = data['patterns']
market_data = data['market']
network_data = data['network']

# Sidebar stats
st.sidebar.header("⚡ System Status")
st.sidebar.metric("Total Cauldrons", len(df_cauldrons))
st.sidebar.metric("Data Points", f"{len(df_levels):,}")
st.sidebar.metric("High Risk Cauldrons", len(df_overflow[df_overflow['risk_level'] == 'HIGH']))

if len(data['matched']) > 0:
    summary = analysis.get_matching_summary(data['matched'])
    st.sidebar.metric("Matching Accuracy", f"{summary['accuracy_pct']:.1f}%")
    st.sidebar.metric("Unaccounted Volume", f"{summary['total_unaccounted']:.0f}L")
    
st.sidebar.markdown("---")
st.sidebar.header("🚨 Fraud Detection")
st.sidebar.metric("Missing Tickets", patterns['missing_tickets'])
st.sidebar.metric("Systematic Theft Cases", len(patterns['systematic_theft']))
st.sidebar.metric("Total Unaccounted", f"{patterns['total_unaccounted']:.0f}L")

# Tabs for different views
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ Network Map", "🎫 Ticket Validation", "👩‍🦰 Witch Performance", "⚠️ Overflow Priority", "📊 Cauldron Details"])

with tab1:
    st.subheader("Potion Network Map")
    st.markdown("**Map Legend:** Marker size indicates utilization | Color indicates risk level | Hover for details")
    
    map_fig = plot_cauldron_map(df_cauldrons, market_data, df_overflow, network_data, df_levels, df_fill_rates)
    st.plotly_chart(map_fig, use_container_width=True)
    
    # Network Metrics Section
    st.markdown("---")
    st.subheader("📊 Network Metrics")
    
    # Calculate summary metrics
    total_cauldrons = len(df_cauldrons)
    total_capacity = df_cauldrons['max_volume'].sum() if 'max_volume' in df_cauldrons.columns else 0
    current_total_level = df_overflow['current_level'].sum() if len(df_overflow) > 0 else 0
    avg_utilization = df_overflow['utilization_pct'].mean() if len(df_overflow) > 0 else 0
    high_risk_count = len(df_overflow[df_overflow['risk_level'] == 'HIGH']) if len(df_overflow) > 0 else 0
    medium_risk_count = len(df_overflow[df_overflow['risk_level'] == 'MEDIUM']) if len(df_overflow) > 0 else 0
    low_risk_count = len(df_overflow[df_overflow['risk_level'] == 'LOW']) if len(df_overflow) > 0 else 0
    avg_fill_rate = df_fill_rates['fill_rate_per_hour'].mean() if len(df_fill_rates) > 0 else 0
    total_drain_events = len(data['drain_events'])
    total_tickets = len(data['tickets'])
    
    # Display metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Cauldrons", total_cauldrons)
        st.metric("Total Capacity", f"{total_capacity:.0f}L")
    with col2:
        st.metric("Current Total Level", f"{current_total_level:.0f}L")
        st.metric("Avg Utilization", f"{avg_utilization:.1f}%")
    with col3:
        st.metric("High Risk Cauldrons", high_risk_count, delta=f"Medium: {medium_risk_count}, Low: {low_risk_count}")
        st.metric("Avg Fill Rate", f"{avg_fill_rate:.2f} L/h")
    with col4:
        st.metric("Total Drain Events", total_drain_events)
        st.metric("Total Tickets", total_tickets)
    
    # Risk Distribution
    st.markdown("### Risk Level Distribution")
    st.caption("High Risk: < 12 hours to overflow | Medium Risk: 12-24 hours | Low Risk: > 24 hours")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🔴 High Risk", high_risk_count)
    with col2:
        st.metric("🟠 Medium Risk", medium_risk_count)
    with col3:
        st.metric("🟢 Low Risk", low_risk_count)
    
    # Cauldron Details Table
    if len(df_overflow) > 0:
        st.markdown("### Cauldron Status Summary")
        display_columns = ['cauldron_id', 'current_level', 'max_volume', 'utilization_pct', 
                          'hours_to_overflow', 'risk_level']
        df_display = df_overflow[display_columns].copy()
        df_display.columns = ['Cauldron ID', 'Current Level (L)', 'Max Volume (L)', 
                             'Utilization (%)', 'Hours to Overflow', 'Risk Level']
        df_display = df_display.sort_values('Hours to Overflow')
        
        # Color code by risk level
        def color_risk(val):
            if val == 'HIGH':
                return 'background-color: #ffcccc'
            elif val == 'MEDIUM':
                return 'background-color: #ffe6cc'
            else:
                return 'background-color: #ccffcc'
        
        st.dataframe(
            df_display.style.applymap(color_risk, subset=['Risk Level']),
            use_container_width=True,
            height=400
        )

with tab2:
    st.subheader("Daily Ticket Reconciliation")
    st.markdown("**Legend:** ✓ Valid | ⚠️ Suspicious | ✗ Missing Ticket")
    
    if len(df_reconciliation) > 0:
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_status = st.multiselect("Filter by Status", 
                                          df_reconciliation['status'].unique(),
                                          default=df_reconciliation['status'].unique())
        with col2:
            filter_cauldron = st.multiselect("Filter by Cauldron",
                                           df_reconciliation['cauldron_id'].unique())
        with col3:
            filter_courier = st.multiselect("Filter by Courier",
                                          df_reconciliation['courier_id'].unique())
        
        # Apply filters
        df_filtered = df_reconciliation[df_reconciliation['status'].isin(filter_status)]
        if filter_cauldron:
            df_filtered = df_filtered[df_filtered['cauldron_id'].isin(filter_cauldron)]
        if filter_courier:
            df_filtered = df_filtered[df_filtered['courier_id'].isin(filter_courier)]
        
        # Display table with color coding
        st.dataframe(
            df_filtered.style.applymap(
                lambda x: 'background-color: #90EE90' if x == '✓ Valid' else 
                         ('background-color: #FFD700' if '⚠️' in str(x) else 
                          ('background-color: #FF6B6B' if '✗' in str(x) else '')),
                subset=['status']
            ),
            use_container_width=True,
            height=400
        )
        
        # Summary stats
        st.markdown("### Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            valid = len(df_filtered[df_filtered['status'] == '✓ Valid'])
            st.metric("Valid Tickets", valid)
        with col2:
            suspicious = len(df_filtered[df_filtered['status'].str.contains('⚠️')])
            st.metric("Suspicious", suspicious)
        with col3:
            missing = len(df_filtered[df_filtered['status'].str.contains('✗')])
            st.metric("Missing", missing)
        with col4:
            total_disc = df_filtered['discrepancy'].sum()
            st.metric("Total Discrepancy", f"{total_disc:.1f}L")
    else:
        st.info("No reconciliation data available")

with tab3:
    st.subheader("Courier Witch Performance Scorecard")
    
    if len(df_witch_perf) > 0:
        # Display performance cards
        for _, witch in df_witch_perf.iterrows():
            risk_color = {
                'HIGH RISK': '🔴',
                'MODERATE': '🟡',
                'RELIABLE': '🟢'
            }.get(witch['risk_level'], '⚪')
            
            with st.expander(f"{risk_color} {witch['courier_id']} - Trust Score: {witch['trust_score']:.0f}%"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Collections", int(witch['total_collections']))
                    st.metric("Matched Tickets", int(witch['matched_tickets']))
                with col2:
                    st.metric("Suspicious Tickets", int(witch['suspicious_tickets']))
                    st.metric("Avg Discrepancy", f"{witch['avg_discrepancy']:.2f}L")
                with col3:
                    st.metric("Trust Score", f"{witch['trust_score']:.0f}%")
                    st.metric("Risk Level", witch['risk_level'])
        
        # Visualization
        st.markdown("### Trust Score Comparison")
        fig = go.Figure()
        colors = df_witch_perf['risk_level'].map({
            'HIGH RISK': 'red',
            'MODERATE': 'orange',
            'RELIABLE': 'green'
        })
        fig.add_trace(go.Bar(
            x=df_witch_perf['courier_id'],
            y=df_witch_perf['trust_score'],
            marker_color=colors,
            text=df_witch_perf['trust_score'].round(0),
            textposition='outside'
        ))
        fig.update_layout(
            title="Courier Trust Scores",
            xaxis_title="Courier ID",
            yaxis_title="Trust Score (%)",
            yaxis_range=[0, 105],
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No witch performance data available")

with tab4:
    st.subheader("Overflow Risk & Priority Timeline")
    
    if len(df_priority) > 0:
        # Display priority list
        st.markdown("### Collection Priority Ranking")
        for idx, row in df_priority.iterrows():
            priority_emoji = {
                'CRITICAL - OVERDUE': '🚨',
                'URGENT': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }.get(row['priority'], '⚪')
            
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.markdown(f"**{priority_emoji} {row['cauldron_id']}**")
            with col2:
                st.text(f"{row['current_level']:.0f}/{row['max_volume']:.0f}L")
            with col3:
                st.text(f"⏱️ {row['effective_hours']:.1f}h remaining")
            with col4:
                st.text(row['priority'])
        
        # Visualization
        st.markdown("### Hours to Overflow")
        fig = go.Figure()
        colors = df_priority['priority'].map({
            'CRITICAL - OVERDUE': 'red',
            'URGENT': 'orangered',
            'HIGH': 'orange',
            'MEDIUM': 'yellow',
            'LOW': 'green'
        })
        fig.add_trace(go.Bar(
            y=df_priority['cauldron_id'],
            x=df_priority['effective_hours'],
            orientation='h',
            marker_color=colors,
            text=df_priority['effective_hours'].round(1),
            textposition='outside'
        ))
        fig.update_layout(
            title="Effective Hours to Overflow (accounting for travel time)",
            xaxis_title="Hours",
            yaxis_title="Cauldron",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No overflow priority data available")

with tab5:
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



