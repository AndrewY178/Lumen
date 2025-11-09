import pandas as pd
import numpy as np

class Analytics:
    @staticmethod
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
                    remaining_capacity = max_volume - current_level
                    hours_to_overflow = (remaining_capacity / fill_rate_per_min) / 60
                    utilization_pct = (current_level / max_volume) * 100
                    
                    overflow_analysis.append({
                        'cauldron_id': cauldron_id,
                        'current_level': current_level,
                        'max_volume': max_volume,
                        'remaining_capacity': remaining_capacity,
                        'utilization_pct': utilization_pct,
                        'fill_rate_per_hour': fill_rate_per_min * 60,
                        'hours_to_overflow': hours_to_overflow,
                        'risk_level': 'HIGH' if hours_to_overflow < 12 else ('MEDIUM' if hours_to_overflow < 24 else 'LOW')
                    })
        
        return pd.DataFrame(overflow_analysis)
    
    @staticmethod
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
    
    @staticmethod
    def get_top_suspicious_cauldrons(df_matched: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
        if len(df_matched) == 0:
            return pd.DataFrame()
        
        under_reported = df_matched[df_matched['status'] == 'UNDER_REPORTED']
        if len(under_reported) == 0:
            return pd.DataFrame()
        
        return under_reported.groupby('cauldron_id').agg({
            'difference': lambda x: abs(x.sum()),
            'drain_amount': 'count'
        }).sort_values('difference', ascending=False).head(top_n).rename(columns={
            'difference': 'missing_volume',
            'drain_amount': 'event_count'
        })

