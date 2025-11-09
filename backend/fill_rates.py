"""Fill rate calculation functions"""
import pandas as pd


def calculate_fill_rates(df_levels: pd.DataFrame) -> pd.DataFrame:
    """Calculate fill rates for each cauldron.
    
    Uses median of positive rate changes during filling periods (robust to outliers).
    
    Args:
        df_levels: DataFrame with cauldron level data over time
        
    Returns:
        DataFrame with fill rates (per minute and per hour) for each cauldron
    """
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

