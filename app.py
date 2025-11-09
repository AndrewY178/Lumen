"""Main Streamlit application for Potion Flow Monitoring Dashboard"""
import streamlit as st
import plotly.graph_objects as go
from data_loader import load_data
from visualizations import plot_cauldron_map, plot_level_timeseries, plot_rate_of_change
from drain_detection import get_matching_summary
from data_transforms import get_cauldron_ids

st.set_page_config(page_title="🧙 Potion Flow Monitor", layout="wide")

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
    summary = get_matching_summary(data['matched'])
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
    cauldron_ids = get_cauldron_ids(df_levels)
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
