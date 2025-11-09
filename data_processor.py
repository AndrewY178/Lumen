import pandas as pd
import numpy as np
from typing import Dict, Optional, List

class DataProcessor:
    @staticmethod
    def _normalize_json_data(data: Dict, key: Optional[str] = None) -> List:
        if isinstance(data, list):
            return data
        elif key and key in data:
            return data[key]
        return [data]
    
    @staticmethod
    def transform_level_data(level_data: Dict) -> pd.DataFrame:
        records = DataProcessor._normalize_json_data(level_data, 'data')
        df = pd.json_normalize(records)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
        return df
    
    @staticmethod
    def transform_tickets(tickets_data: Dict) -> pd.DataFrame:
        tickets = DataProcessor._normalize_json_data(tickets_data, 'transport_tickets')
        df = pd.DataFrame(tickets)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    @staticmethod
    def transform_cauldrons(cauldrons_data: Dict) -> pd.DataFrame:
        cauldrons = DataProcessor._normalize_json_data(cauldrons_data)
        df = pd.DataFrame(cauldrons)
        if 'id' in df.columns:
            df = df.set_index('id')
        return df
    
    @staticmethod
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
            
            # Calculate fill rate from positive rates (when level is increasing)
            positive_rates = rates[rates > 0]
            if len(positive_rates) > 0:
                median_fill_rate = positive_rates.median()
                fill_rates.append({
                    'cauldron': col,
                    'fill_rate_per_min': median_fill_rate,
                    'fill_rate_per_hour': median_fill_rate * 60
                })
        
        return pd.DataFrame(fill_rates)
    
    @staticmethod
    def get_cauldron_ids(df_levels: pd.DataFrame) -> List[str]:
        return [col.replace('cauldron_levels.', '') for col in df_levels.columns if 'cauldron' in col.lower()]

