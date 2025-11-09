"""Fill rate calculation functions"""
import pandas as pd
import numpy as np
from scipy import stats


def _identify_filling_segments(series: pd.Series, min_segment_duration_min: int = 120,
                              window_minutes: int = 180) -> list:
    """Identify filling segments using rolling window analysis.
    
    Analyzes the time series in windows and identifies periods with consistent
    upward trends using linear regression.
    
    Args:
        series: Time series of cauldron levels
        min_segment_duration_min: Minimum duration in minutes for a valid segment
        window_minutes: Window size in minutes for analysis
        
    Returns:
        List of tuples (start_idx, end_idx, start_time, end_time) for each segment
    """
    if len(series) < 10:
        return []
    
    segments = []
    sample_interval_min = (series.index[1] - series.index[0]).total_seconds() / 60
    window_size = max(10, int(window_minutes / sample_interval_min))
    
    i = 0
    while i + window_size < len(series):
        window_data = series.iloc[i:i+window_size]
        window_times = window_data.index
        window_levels = window_data.values
        
        if len(window_data) < 3:
            i += window_size // 2
            continue
        
        time_minutes = (window_times - window_times[0]).total_seconds() / 60
        level_change = window_levels[-1] - window_levels[0]
        
        if level_change > 5:
            slope, intercept, r_value, p_value, std_err = stats.linregress(time_minutes, window_levels)
            
            if r_value > 0.85 and slope > 0:
                start_time = window_times[0]
                end_time = window_times[-1]
                duration_min = (end_time - start_time).total_seconds() / 60
                
                if duration_min >= min_segment_duration_min:
                    segments.append((i, i+window_size-1, start_time, end_time))
        
        i += window_size // 2
    
    merged_segments = []
    if segments:
        merged_segments.append(segments[0])
        for seg in segments[1:]:
            last_seg = merged_segments[-1]
            if seg[2] <= last_seg[3] + pd.Timedelta(minutes=60):
                merged_segments[-1] = (last_seg[0], seg[1], last_seg[2], seg[3])
            else:
                merged_segments.append(seg)
    
    return merged_segments


def _calculate_segment_rate(series: pd.Series, start_idx: int, end_idx: int,
                           start_time: pd.Timestamp, end_time: pd.Timestamp) -> float:
    """Calculate fill rate for a segment using linear regression.
    
    Args:
        series: Time series data
        start_idx: Start index of segment
        end_idx: End index of segment
        start_time: Start timestamp
        end_time: End timestamp
        
    Returns:
        Fill rate in L/min
    """
    segment_data = series.iloc[start_idx:end_idx+1]
    
    if len(segment_data) < 2:
        return np.nan
    
    time_minutes = (segment_data.index - start_time).total_seconds() / 60
    levels = segment_data.values
    
    if len(segment_data) >= 3:
        slope, intercept, r_value, p_value, std_err = stats.linregress(time_minutes, levels)
        if r_value > 0.7:
            return slope
    else:
        level_change = levels[-1] - levels[0]
        time_change = time_minutes[-1] - time_minutes[0]
        if time_change > 0:
            return level_change / time_change
    
    return np.nan


def calculate_fill_rates(df_levels: pd.DataFrame, min_segment_duration_min: int = 120,
                        use_percentile: float = 25.0) -> pd.DataFrame:
    """Calculate fill rates from long-term filling trends.
    
    Identifies continuous filling segments and calculates rates using linear regression.
    Uses percentile (default 25th) to get steady-state rate, avoiding high outliers.
    
    Args:
        df_levels: DataFrame with cauldron level data over time
        min_segment_duration_min: Minimum duration for a valid filling segment (minutes)
        use_percentile: Percentile to use for fill rate (lower = more conservative)
        
    Returns:
        DataFrame with fill rates (per minute and per hour) for each cauldron
    """
    fill_rates = []
    cauldron_cols = [col for col in df_levels.columns if 'cauldron' in col.lower()]
    
    for col in cauldron_cols:
        series = df_levels[col].dropna()
        if len(series) < 10:
            continue
        
        segments = _identify_filling_segments(series, min_segment_duration_min)
        
        if len(segments) == 0:
            continue
        
        segment_rates = []
        for start_idx, end_idx, start_time, end_time in segments:
            rate = _calculate_segment_rate(series, start_idx, end_idx, start_time, end_time)
            if not np.isnan(rate) and rate > 0:
                segment_rates.append(rate)
        
        if len(segment_rates) == 0:
            continue
        
        segment_rates = np.array(segment_rates)
        
        if use_percentile is not None:
            fill_rate = np.percentile(segment_rates, use_percentile)
        else:
            fill_rate = np.median(segment_rates)
        
        fill_rates.append({
            'cauldron': col,
            'fill_rate_per_min': fill_rate,
            'fill_rate_per_hour': fill_rate * 60,
            'num_segments': len(segment_rates),
            'median_segment_rate': np.median(segment_rates),
            'mean_segment_rate': np.mean(segment_rates)
        })
    
    return pd.DataFrame(fill_rates)

