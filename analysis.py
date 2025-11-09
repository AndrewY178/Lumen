import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Config
BASE_URL = "https://hackutd2025.eog.systems"
MARKET_UNLOAD_TIME = 15
NEGATIVE_RATE_THRESHOLD = -0.05
MIN_DRAIN_VOLUME = 20.0
TICKET_TOLERANCE_PCT = 2.0

# Global cache
_cache = {}

def fetch_api_data(endpoint: str, use_cache: bool = True) -> Dict:
    if use_cache and endpoint in _cache:
        return _cache[endpoint]
    
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        _cache[endpoint] = data
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {endpoint}: {e}")
        return {}

def fetch_travel_times(cauldron_ids: List[str]) -> Dict[str, float]:
    travel_times = {}
    for cauldron_id in cauldron_ids:
        neighbors = fetch_api_data(f'/api/Information/graph/neighbors/{cauldron_id}')
        if isinstance(neighbors, list):
            for neighbor in neighbors:
                if neighbor.get('to', '').startswith('market'):
                    cost_str = neighbor.get('cost', '00:00:00')
                    time_parts = cost_str.split(':')
                    if len(time_parts) == 3:
                        h, m, s = int(time_parts[0]), int(time_parts[1]), int(time_parts[2])
                        travel_times[cauldron_id] = h * 60 + m + s / 60
                        break
    return travel_times

def fetch_all_data() -> Dict:
    return {
        'level_data': fetch_api_data('/api/Data/?start_date=0&end_date=2000000000'),
        'tickets': fetch_api_data('/api/Tickets'),
        'cauldrons': fetch_api_data('/api/Information/cauldrons'),
        'network': fetch_api_data('/api/Information/network'),
        'couriers': fetch_api_data('/api/Information/couriers'),
        'market': fetch_api_data('/api/Information/market')
    }

def _normalize_json(data: Dict, key: Optional[str] = None) -> List:
    if isinstance(data, list):
        return data
    elif key and key in data:
        return data[key]
    return [data]

def transform_level_data(level_data: Dict) -> pd.DataFrame:
    records = _normalize_json(level_data, 'data')
    df = pd.json_normalize(records)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
    return df

def transform_tickets(tickets_data: Dict) -> pd.DataFrame:
    tickets = _normalize_json(tickets_data, 'transport_tickets')
    df = pd.DataFrame(tickets)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    return df

def transform_cauldrons(cauldrons_data: Dict) -> pd.DataFrame:
    cauldrons = _normalize_json(cauldrons_data)
    df = pd.DataFrame(cauldrons)
    if 'id' in df.columns:
        df = df.set_index('id')
    return df

def calculate_fill_rates(df_levels: pd.DataFrame) -> pd.DataFrame:
    fill_rates = []
    cauldron_cols = [col for col in df_levels.columns if 'cauldron' in col.lower()]
    
    for col in cauldron_cols:
        series = df_levels[col].dropna()
        if len(series) < 2:
            continue
        
        time_diffs = series.index.to_series().diff().dt.total_seconds() / 60
        level_diffs = series.diff()
        rates = level_diffs / time_diffs
        positive_rates = rates[rates > 0]
        
        if len(positive_rates) > 0:
            median_fill_rate = positive_rates.median()
            fill_rates.append({
                'cauldron': col,
                'fill_rate_per_min': median_fill_rate,
                'fill_rate_per_hour': median_fill_rate * 60
            })
    
    return pd.DataFrame(fill_rates)

def get_cauldron_ids(df_levels: pd.DataFrame) -> List[str]:
    return [col.replace('cauldron_levels.', '') for col in df_levels.columns if 'cauldron' in col.lower()]

def _calc_ticket_date(drain_end: datetime, travel_time: float) -> datetime.date:
    return (drain_end + timedelta(minutes=travel_time)).date()

def detect_drain_events(series: pd.Series, cauldron_id: str, fill_rate: float,
                       travel_time: float = 0) -> pd.DataFrame:
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

def calculate_overflow_risk(df_levels: pd.DataFrame, df_cauldrons: pd.DataFrame, 
                            df_fill_rates: pd.DataFrame) -> pd.DataFrame:
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

def get_daily_reconciliation(df_matched: pd.DataFrame, df_tickets: pd.DataFrame) -> pd.DataFrame:
    """Daily reconciliation table with discrepancies"""
    if len(df_matched) == 0:
        return pd.DataFrame()
    
    reconciliation = []
    for _, row in df_matched.iterrows():
        ticket_info = df_tickets[df_tickets['ticket_id'] == row['ticket_id']]
        courier_id = ticket_info['courier_id'].values[0] if len(ticket_info) > 0 else 'Unknown'
        
        status_symbol = {
            'MATCHED': '✓ Valid',
            'UNDER_REPORTED': '⚠️ Suspicious',
            'OVER_REPORTED': '⚠️ Over-reported',
            'NO_TICKET_FOUND': '✗ Missing Ticket'
        }.get(row['status'], '?')
        
        reconciliation.append({
            'date': row['drain_date'],
            'cauldron_id': row['cauldron_id'],
            'drain_volume': row['drain_amount'],
            'ticket_volume': row['ticket_amount'] if pd.notna(row['ticket_amount']) else 0,
            'discrepancy': row['difference'] if pd.notna(row['difference']) else -row['drain_amount'],
            'status': status_symbol,
            'courier_id': courier_id,
            'notes': row['notes']
        })
    
    df = pd.DataFrame(reconciliation)
    if len(df) > 0:
        df = df.sort_values(['date', 'cauldron_id'])
    return df

def get_witch_performance(df_matched: pd.DataFrame, df_tickets: pd.DataFrame) -> pd.DataFrame:
    """Calculate per-courier performance metrics and trust scores"""
    if len(df_matched) == 0 or len(df_tickets) == 0:
        return pd.DataFrame()
    
    courier_metrics = []
    courier_ids = df_tickets['courier_id'].unique()
    
    for courier_id in courier_ids:
        courier_tickets = df_tickets[df_tickets['courier_id'] == courier_id]
        courier_matches = df_matched[df_matched['ticket_id'].isin(courier_tickets['ticket_id'])]
        
        if len(courier_matches) == 0:
            continue
        
        total_collections = len(courier_matches)
        avg_discrepancy = courier_matches['difference'].mean() if 'difference' in courier_matches.columns else 0
        suspicious_count = len(courier_matches[courier_matches['status'].isin(['UNDER_REPORTED', 'NO_TICKET_FOUND'])])
        matched_count = len(courier_matches[courier_matches['status'] == 'MATCHED'])
        
        trust_score = max(0, 100 - (abs(avg_discrepancy) * 5) - (suspicious_count * 10))
        trust_score = min(100, trust_score)
        
        risk_level = 'HIGH RISK' if trust_score < 40 else ('MODERATE' if trust_score < 70 else 'RELIABLE')
        
        courier_metrics.append({
            'courier_id': courier_id,
            'total_collections': total_collections,
            'matched_tickets': matched_count,
            'suspicious_tickets': suspicious_count,
            'avg_discrepancy': avg_discrepancy,
            'trust_score': trust_score,
            'risk_level': risk_level
        })
    
    df = pd.DataFrame(courier_metrics)
    if len(df) > 0:
        df = df.sort_values('trust_score')
    return df

def get_overflow_priority(df_overflow: pd.DataFrame, travel_times: dict) -> pd.DataFrame:
    """Rank cauldrons by overflow urgency with scheduling constraints"""
    if len(df_overflow) == 0:
        return pd.DataFrame()
    
    priority_list = []
    for _, cauldron in df_overflow.iterrows():
        cauldron_id = cauldron['cauldron_id']
        hours_to_overflow = cauldron['hours_to_overflow']
        travel_time = travel_times.get(cauldron_id, 0)
        
        collection_time = 15
        total_time_needed = (travel_time + collection_time + 15) / 60
        
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

def get_suspicious_patterns(df_matched: pd.DataFrame) -> Dict:
    """Identify suspicious patterns in discrepancies"""
    if len(df_matched) == 0:
        return {}
    
    patterns = {
        'systematic_theft': [],
        'consistent_under_reporters': [],
        'missing_tickets': [],
        'total_unaccounted': 0
    }
    
    suspicious = df_matched[df_matched['status'].isin(['UNDER_REPORTED', 'NO_TICKET_FOUND'])]
    if len(suspicious) > 0:
        patterns['total_unaccounted'] = abs(suspicious['difference'].sum())
        
        by_cauldron = suspicious.groupby('cauldron_id').agg({
            'difference': lambda x: abs(x.sum()),
            'drain_amount': 'count'
        }).sort_values('difference', ascending=False)
        
        for cauldron_id, row in by_cauldron.head(5).iterrows():
            if row['drain_amount'] >= 3:
                patterns['systematic_theft'].append({
                    'cauldron_id': cauldron_id,
                    'missing_volume': row['difference'],
                    'event_count': row['drain_amount']
                })
    
    no_tickets = df_matched[df_matched['status'] == 'NO_TICKET_FOUND']
    patterns['missing_tickets'] = len(no_tickets)
    
    return patterns
