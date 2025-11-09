"""Reporting and performance metrics functions"""
import pandas as pd
from typing import Dict


def get_daily_reconciliation(df_matched: pd.DataFrame, df_tickets: pd.DataFrame) -> pd.DataFrame:
    """Generate daily reconciliation table with discrepancies.
    
    Args:
        df_matched: DataFrame with matched drains and tickets
        df_tickets: DataFrame with transport tickets
        
    Returns:
        DataFrame with daily reconciliation data
    """
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
    """Calculate per-courier performance metrics and trust scores.
    
    Args:
        df_matched: DataFrame with matched drains and tickets
        df_tickets: DataFrame with transport tickets
        
    Returns:
        DataFrame with courier performance metrics
    """
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


def get_suspicious_patterns(df_matched: pd.DataFrame) -> Dict:
    """Identify suspicious patterns in discrepancies.
    
    Args:
        df_matched: DataFrame with matched drains and tickets
        
    Returns:
        Dictionary with suspicious patterns identified
    """
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

