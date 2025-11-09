"""Data transformation utilities for converting API data to DataFrames"""
import pandas as pd
from typing import Dict, List, Optional


def _normalize_json(data: Dict, key: Optional[str] = None) -> List:
    """Helper function to normalize JSON data structure.
    
    Args:
        data: JSON data (dict or list)
        key: Optional key to extract from dict
        
    Returns:
        List of records
    """
    if isinstance(data, list):
        return data
    elif key and key in data:
        return data[key]
    return [data]


def transform_level_data(level_data: Dict) -> pd.DataFrame:
    """Transform raw level data into time-indexed DataFrame.
    
    Args:
        level_data: Raw level data from API
        
    Returns:
        DataFrame with timestamp index and cauldron level columns
    """
    records = _normalize_json(level_data, 'data')
    df = pd.json_normalize(records)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
    return df


def transform_tickets(tickets_data: Dict) -> pd.DataFrame:
    """Transform tickets data into DataFrame.
    
    Args:
        tickets_data: Raw tickets data from API
        
    Returns:
        DataFrame with ticket information
    """
    tickets = _normalize_json(tickets_data, 'transport_tickets')
    df = pd.DataFrame(tickets)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    return df


def transform_cauldrons(cauldrons_data: Dict) -> pd.DataFrame:
    """Transform cauldrons metadata into DataFrame.
    
    Args:
        cauldrons_data: Raw cauldrons data from API
        
    Returns:
        DataFrame with cauldron information, indexed by cauldron ID
    """
    cauldrons = _normalize_json(cauldrons_data)
    df = pd.DataFrame(cauldrons)
    if 'id' in df.columns:
        df = df.set_index('id')
    return df


def get_cauldron_ids(df_levels: pd.DataFrame) -> List[str]:
    """Extract cauldron IDs from level data columns.
    
    Args:
        df_levels: DataFrame with cauldron level data
        
    Returns:
        List of cauldron IDs
    """
    return [col.replace('cauldron_levels.', '') for col in df_levels.columns if 'cauldron' in col.lower()]

