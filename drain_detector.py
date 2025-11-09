import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import config

class DrainDetector:
    @staticmethod
    def _calculate_ticket_date(drain_end: datetime, travel_time_minutes: float) -> datetime.date:
        arrival_at_market = drain_end + timedelta(minutes=travel_time_minutes)
        return arrival_at_market.date()
    
    @staticmethod
    def detect_drain_events(series: pd.Series, cauldron_id: str, 
                           fill_rate: float,
                           travel_time_minutes: float = 0,
                           negative_rate_threshold: float = None,
                           min_drop_volume: float = None) -> pd.DataFrame:
        
        if negative_rate_threshold is None:
            negative_rate_threshold = config.NEGATIVE_RATE_THRESHOLD
        if min_drop_volume is None:
            min_drop_volume = config.MIN_DRAIN_VOLUME
        
        series = series.dropna()
        if len(series) < 3:
            return pd.DataFrame()
        
        time_diffs = series.index.to_series().diff().dt.total_seconds() / 60
        level_diffs = series.diff()
        rates = level_diffs / time_diffs
        
        is_draining = rates < negative_rate_threshold
        
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
                    peak_time = timestamp
                
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
                    potion_generated_during_drain = fill_rate * drain_duration
                    total_collected = level_drop + potion_generated_during_drain
                    
                    if level_drop >= min_drop_volume and total_collected > 0:
                        ticket_date = DrainDetector._calculate_ticket_date(drain_end, travel_time_minutes)
                        drain_events.append({
                            'cauldron_id': cauldron_id,
                            'start_time': drain_start,
                            'end_time': drain_end,
                            'date': drain_end.date(),
                            'ticket_date': ticket_date,
                            'level_before': level_before,
                            'level_after': level_after,
                            'level_drop': level_drop,
                            'drain_duration_min': drain_duration,
                            'potion_generated_during_drain': potion_generated_during_drain,
                            'total_collected': total_collected,
                            'min_rate_during_drain': rates.iloc[drain_start_idx:drain_end_idx].min()
                        })
                    
                    in_drain = False
                    drain_start = None
                    drain_start_idx = None
                    peak_level = level
        
        return pd.DataFrame(drain_events)
    
    @staticmethod
    def detect_all_drains(df_levels: pd.DataFrame, fill_rates: dict, travel_times: dict) -> pd.DataFrame:
        cauldron_cols = [col for col in df_levels.columns if 'cauldron' in col.lower()]
        all_drain_events = []
        
        for col in cauldron_cols:
            cauldron_id = col.replace('cauldron_levels.', '')
            fill_rate = fill_rates.get(col, np.nan)
            travel_time = travel_times.get(cauldron_id, 0)
            
            if np.isnan(fill_rate) or fill_rate <= 0:
                continue
            
            events = DrainDetector.detect_drain_events(
                df_levels[col], 
                cauldron_id, 
                fill_rate,
                travel_time_minutes=travel_time
            )
            all_drain_events.append(events)
        
        if len(all_drain_events) > 0 and any(len(df) > 0 for df in all_drain_events):
            df_drain_events = pd.concat([df for df in all_drain_events if len(df) > 0], ignore_index=True)
            return df_drain_events.sort_values('end_time')
        
        return pd.DataFrame()

