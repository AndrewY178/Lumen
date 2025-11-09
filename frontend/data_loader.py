"""Data loading and caching for Streamlit app"""
import streamlit as st
import pandas as pd
from backend.api import fetch_all_data, fetch_travel_times
from backend.data_transforms import transform_level_data, transform_tickets, transform_cauldrons, get_cauldron_ids
from backend.fill_rates import calculate_fill_rates
from backend.drain_detection import detect_all_drains, match_drains_to_tickets
from backend.analytics import calculate_overflow_risk, get_overflow_priority
from backend.reporting import get_daily_reconciliation, get_witch_performance, get_suspicious_patterns


@st.cache_data
def load_data():
    """Load and process all data for the dashboard.
    
    This function is cached by Streamlit to avoid recomputing on every rerun.
    
    Returns:
        Dictionary containing all processed data:
        - levels: DataFrame with cauldron levels
        - tickets: DataFrame with transport tickets
        - cauldrons: DataFrame with cauldron information
        - drain_events: DataFrame with detected drain events
        - matched: DataFrame with matched drains and tickets
        - fill_rates: DataFrame with fill rates
        - overflow: DataFrame with overflow risk analysis
        - reconciliation: DataFrame with daily reconciliation
        - witch_perf: DataFrame with courier performance
        - priority: DataFrame with overflow priority ranking
        - patterns: Dictionary with suspicious patterns
        - couriers: DataFrame with courier information
        - market: Dictionary with market information
        - network: Dictionary with network graph data
        - travel_times: Dictionary with travel times
    """
    raw_data = fetch_all_data()
    
    df_levels = transform_level_data(raw_data['level_data'])
    df_tickets = transform_tickets(raw_data['tickets'])
    df_cauldrons = transform_cauldrons(raw_data['cauldrons'])
    df_fill_rates = calculate_fill_rates(df_levels)
    
    fill_rates = dict(zip(df_fill_rates['cauldron'], df_fill_rates['fill_rate_per_min']))
    cauldron_ids = get_cauldron_ids(df_levels)
    travel_times = fetch_travel_times(cauldron_ids)
    
    df_drain_events = detect_all_drains(df_levels, fill_rates, travel_times)
    df_matched = match_drains_to_tickets(df_drain_events, df_tickets)
    df_overflow = calculate_overflow_risk(df_levels, df_cauldrons, df_fill_rates)
    
    df_reconciliation = get_daily_reconciliation(df_matched, df_tickets)
    df_witch_perf = get_witch_performance(df_matched, df_tickets)
    df_priority = get_overflow_priority(df_overflow, travel_times)
    patterns = get_suspicious_patterns(df_matched)
    
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

