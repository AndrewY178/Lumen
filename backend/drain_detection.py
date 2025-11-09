"""Drain event detection and ticket matching"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict
from .config import NEGATIVE_RATE_THRESHOLD, MIN_DRAIN_VOLUME, TICKET_TOLERANCE_PCT


def _calc_ticket_date(drain_end: datetime, travel_time: float):
    """Calculate expected ticket date based on drain end time and travel time.
    
    Args:
        drain_end: Drain end timestamp
        travel_time: Travel time in minutes
        
    Returns:
        Expected ticket date
    """
    return (drain_end + timedelta(minutes=travel_time)).date()


def detect_drain_events(series: pd.Series, cauldron_id: str, fill_rate: float,
                       travel_time: float = 0) -> pd.DataFrame:
    """Detect drain events for a single cauldron.
    
    Uses rate-of-change based detection with continuous filling compensation.
    
    Args:
        series: Time series of cauldron levels
        cauldron_id: ID of the cauldron
        fill_rate: Fill rate in L/min
        travel_time: Travel time to market in minutes
        
    Returns:
        DataFrame with detected drain events
    """
    series = series.dropna()
    if len(series) < 3:
        return pd.DataFrame()
    
    time_diffs = series.index.to_series().diff().dt.total_seconds() / 60
    level_diffs = series.diff()
    rates = level_diffs / time_diffs
    is_draining = rates < NEGATIVE_RATE_THRESHOLD
    
    drain_events = []
    in_drain = False
    drain_start = None
    drain_start_idx = None
    peak_level = None
    
    for i in range(len(series)):
        timestamp = series.index[i]
        level = series.iloc[i]
        is_drain_point = is_draining.iloc[i] if i < len(is_draining) else False
        
        if not in_drain:
            if peak_level is None or level > peak_level:
                peak_level = level
            if is_drain_point:
                in_drain = True
                drain_start = timestamp
                drain_start_idx = i
        else:
            if not is_drain_point:
                drain_end = timestamp
                drain_end_idx = i
                level_after = level
                level_before = peak_level
                level_drop = level_before - level_after
                drain_duration = (drain_end - drain_start).total_seconds() / 60
                potion_generated = fill_rate * drain_duration
                total_collected = level_drop + potion_generated
                
                if level_drop >= MIN_DRAIN_VOLUME and total_collected > 0:
                    drain_events.append({
                        'cauldron_id': cauldron_id,
                        'start_time': drain_start,
                        'end_time': drain_end,
                        'date': drain_end.date(),
                        'ticket_date': _calc_ticket_date(drain_end, travel_time),
                        'level_before': level_before,
                        'level_after': level_after,
                        'level_drop': level_drop,
                        'drain_duration_min': drain_duration,
                        'potion_generated_during_drain': potion_generated,
                        'total_collected': total_collected,
                        'min_rate_during_drain': rates.iloc[drain_start_idx:drain_end_idx].min()
                    })
                
                in_drain = False
                peak_level = level
    
    return pd.DataFrame(drain_events)


def detect_all_drains(df_levels: pd.DataFrame, fill_rates: dict, travel_times: dict) -> pd.DataFrame:
    """Detect drain events for all cauldrons.
    
    Args:
        df_levels: DataFrame with level data for all cauldrons
        fill_rates: Dictionary mapping cauldron column names to fill rates
        travel_times: Dictionary mapping cauldron IDs to travel times
        
    Returns:
        DataFrame with all detected drain events
    """
    cauldron_cols = [col for col in df_levels.columns if 'cauldron' in col.lower()]
    all_drains = []
    
    for col in cauldron_cols:
        cauldron_id = col.replace('cauldron_levels.', '')
        fill_rate = fill_rates.get(col, np.nan)
        travel_time = travel_times.get(cauldron_id, 0)
        
        if np.isnan(fill_rate) or fill_rate <= 0:
            continue
        
        events = detect_drain_events(df_levels[col], cauldron_id, fill_rate, travel_time)
        all_drains.append(events)
    
    if all_drains and any(len(df) > 0 for df in all_drains):
        return pd.concat([df for df in all_drains if len(df) > 0], ignore_index=True).sort_values('end_time')
    return pd.DataFrame()


def match_drains_to_tickets(df_drains: pd.DataFrame, df_tickets: pd.DataFrame) -> pd.DataFrame:
    """Match drain events to transport tickets.
    
    Args:
        df_drains: DataFrame with drain events
        df_tickets: DataFrame with transport tickets
        
    Returns:
        DataFrame with matched drains and tickets, including status and discrepancies
    """
    results = []
    
    for _, drain in df_drains.iterrows():
        ticket_date = drain.get('ticket_date', drain['date'])
        cauldron_id = drain['cauldron_id']
        drain_amount = drain['total_collected']
        
        matching_tickets = df_tickets[
            (df_tickets['cauldron_id'] == cauldron_id) & 
            (df_tickets['date'].dt.date == ticket_date)
        ]
        
        if len(matching_tickets) == 0:
            results.append({
                'drain_id': f"{cauldron_id}_{drain['end_time']}",
                'cauldron_id': cauldron_id,
                'drain_date': drain['date'],
                'ticket_date': ticket_date,
                'drain_time': drain['end_time'],
                'drain_amount': drain_amount,
                'ticket_id': None,
                'ticket_amount': None,
                'difference': None,
                'difference_pct': None,
                'status': 'NO_TICKET_FOUND',
                'notes': 'Drain event detected but no ticket reported'
            })
        else:
            best_ticket = min(matching_tickets.iterrows(), 
                            key=lambda x: abs(drain_amount - x[1]['amount_collected']))[1]
            ticket_amount = best_ticket['amount_collected']
            pct_diff = (abs(drain_amount - ticket_amount) / drain_amount) * 100 if drain_amount > 0 else 0
            
            if abs(pct_diff) <= TICKET_TOLERANCE_PCT:
                status = 'MATCHED'
                notes = f'Match (diff: {pct_diff:.2f}%)'
            elif ticket_amount < drain_amount:
                status = 'UNDER_REPORTED'
                notes = f'Under by {drain_amount - ticket_amount:.2f}L ({pct_diff:.2f}%)'
            else:
                status = 'OVER_REPORTED'
                notes = f'Over by {ticket_amount - drain_amount:.2f}L ({pct_diff:.2f}%)'
            
            results.append({
                'drain_id': f"{cauldron_id}_{drain['end_time']}",
                'cauldron_id': cauldron_id,
                'drain_date': drain['date'],
                'ticket_date': ticket_date,
                'drain_time': drain['end_time'],
                'drain_amount': drain_amount,
                'ticket_id': best_ticket['ticket_id'],
                'ticket_amount': ticket_amount,
                'difference': ticket_amount - drain_amount,
                'difference_pct': pct_diff,
                'status': status,
                'notes': notes
            })
    
    return pd.DataFrame(results)


def get_matching_summary(df_matched: pd.DataFrame) -> dict:
    """Get summary statistics for drain-ticket matching.
    
    Args:
        df_matched: DataFrame with matched drains and tickets
        
    Returns:
        Dictionary with matching statistics
    """
    if len(df_matched) == 0:
        return {}
    
    total_drained = df_matched['drain_amount'].sum()
    total_ticketed = df_matched[df_matched['ticket_amount'].notna()]['ticket_amount'].sum()
    
    return {
        'total_drains': len(df_matched),
        'matched': len(df_matched[df_matched['status'] == 'MATCHED']),
        'under_reported': len(df_matched[df_matched['status'] == 'UNDER_REPORTED']),
        'over_reported': len(df_matched[df_matched['status'] == 'OVER_REPORTED']),
        'no_ticket': len(df_matched[df_matched['status'] == 'NO_TICKET_FOUND']),
        'total_drained_volume': total_drained,
        'total_ticketed_volume': total_ticketed,
        'total_unaccounted': total_drained - total_ticketed,
        'accuracy_pct': (len(df_matched[df_matched['status'] == 'MATCHED']) / len(df_matched)) * 100
    }

