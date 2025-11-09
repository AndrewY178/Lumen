"""Analytics and risk calculation functions"""
import pandas as pd
import numpy as np
from typing import Dict


def calculate_overflow_risk(df_levels: pd.DataFrame, df_cauldrons: pd.DataFrame, 
                            df_fill_rates: pd.DataFrame) -> pd.DataFrame:
    """Calculate overflow risk for each cauldron.
    
    Args:
        df_levels: DataFrame with cauldron level data
        df_cauldrons: DataFrame with cauldron information
        df_fill_rates: DataFrame with fill rates for each cauldron
        
    Returns:
        DataFrame with overflow risk analysis for each cauldron
    """
    overflow_analysis = []
    
    for _, cauldron in df_cauldrons.iterrows():
        cauldron_id = cauldron.name if isinstance(cauldron.name, str) else cauldron.get('id', '')
        max_volume = cauldron.get('max_volume', np.nan)
        cauldron_col = f'cauldron_levels.{cauldron_id}'
        
        if cauldron_col not in df_levels.columns:
            continue
        
        current_level = df_levels[cauldron_col].iloc[-1]
        fill_rate_data = df_fill_rates[df_fill_rates['cauldron'] == cauldron_col]
        
        if len(fill_rate_data) > 0:
            fill_rate_per_min = fill_rate_data['fill_rate_per_min'].values[0]
            
            if not np.isnan(max_volume) and not np.isnan(fill_rate_per_min) and fill_rate_per_min > 0:
                remaining = max_volume - current_level
                hours_to_overflow = (remaining / fill_rate_per_min) / 60
                utilization = (current_level / max_volume) * 100
                
                overflow_analysis.append({
                    'cauldron_id': cauldron_id,
                    'current_level': current_level,
                    'max_volume': max_volume,
                    'remaining_capacity': remaining,
                    'utilization_pct': utilization,
                    'fill_rate_per_hour': fill_rate_per_min * 60,
                    'hours_to_overflow': hours_to_overflow,
                    'risk_level': 'HIGH' if hours_to_overflow < 12 else ('MEDIUM' if hours_to_overflow < 24 else 'LOW')
                })
    
    return pd.DataFrame(overflow_analysis)


def get_system_summary(df_levels: pd.DataFrame, df_tickets: pd.DataFrame, 
                      df_drain_events: pd.DataFrame, df_matched: pd.DataFrame,
                      df_fill_rates: pd.DataFrame, df_overflow: pd.DataFrame) -> dict:
    """Get overall system summary statistics.
    
    Args:
        df_levels: DataFrame with level data
        df_tickets: DataFrame with tickets
        df_drain_events: DataFrame with drain events
        df_matched: DataFrame with matched drains and tickets
        df_fill_rates: DataFrame with fill rates
        df_overflow: DataFrame with overflow risk analysis
        
    Returns:
        Dictionary with system summary statistics
    """
    summary = {
        'monitoring_start': df_levels.index.min() if len(df_levels) > 0 else None,
        'monitoring_end': df_levels.index.max() if len(df_levels) > 0 else None,
        'total_cauldrons': len([col for col in df_levels.columns if 'cauldron' in col.lower()]),
        'data_points': len(df_levels),
        'avg_fill_rate': df_fill_rates['fill_rate_per_hour'].mean() if len(df_fill_rates) > 0 else 0,
        'total_drain_events': len(df_drain_events),
        'total_collected': df_drain_events['total_collected'].sum() if len(df_drain_events) > 0 else 0,
        'total_tickets': len(df_tickets),
        'high_risk_cauldrons': len(df_overflow[df_overflow['risk_level'] == 'HIGH']) if len(df_overflow) > 0 else 0,
        'avg_capacity_utilization': df_overflow['utilization_pct'].mean() if len(df_overflow) > 0 else 0
    }
    
    if len(df_matched) > 0:
        summary['matching_accuracy'] = (len(df_matched[df_matched['status'] == 'MATCHED']) / len(df_matched)) * 100
        summary['suspicious_drains'] = len(df_matched[df_matched['status'].isin(['UNDER_REPORTED', 'NO_TICKET_FOUND'])])
        summary['total_unaccounted'] = abs(df_matched[df_matched['difference'] < 0]['difference'].sum())
    
    return summary


def get_overflow_priority(df_overflow: pd.DataFrame, travel_times: dict) -> pd.DataFrame:
    """Rank cauldrons by overflow urgency with scheduling constraints.
    
    Args:
        df_overflow: DataFrame with overflow risk analysis
        travel_times: Dictionary mapping cauldron IDs to travel times in minutes
        
    Returns:
        DataFrame with priority ranking for overflow prevention
    """
    if len(df_overflow) == 0:
        return pd.DataFrame()
    
    priority_list = []
    for _, cauldron in df_overflow.iterrows():
        cauldron_id = cauldron['cauldron_id']
        hours_to_overflow = cauldron['hours_to_overflow']
        travel_time = travel_times.get(cauldron_id, 0)
        
        collection_time = 15  # minutes
        total_time_needed = (travel_time + collection_time + 15) / 60  # convert to hours
        
        effective_hours = hours_to_overflow - total_time_needed
        
        if effective_hours < 0:
            priority = 'CRITICAL - OVERDUE'
            urgency_score = 1000
        elif effective_hours < 6:
            priority = 'URGENT'
            urgency_score = 100 / max(effective_hours, 0.1)
        elif effective_hours < 12:
            priority = 'HIGH'
            urgency_score = 50 / effective_hours
        elif effective_hours < 24:
            priority = 'MEDIUM'
            urgency_score = 20 / effective_hours
        else:
            priority = 'LOW'
            urgency_score = 10 / effective_hours
        
        priority_list.append({
            'cauldron_id': cauldron_id,
            'current_level': cauldron['current_level'],
            'max_volume': cauldron['max_volume'],
            'hours_to_overflow': hours_to_overflow,
            'travel_time_min': travel_time,
            'effective_hours': effective_hours,
            'priority': priority,
            'urgency_score': urgency_score
        })
    
    df = pd.DataFrame(priority_list)
    if len(df) > 0:
        df = df.sort_values('urgency_score', ascending=False)
    return df

