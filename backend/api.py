"""API data fetching functions for Potion Flow Monitoring System"""
import requests
from typing import Dict, List
from .config import BASE_URL

# Global cache for API responses
_cache = {}


def fetch_api_data(endpoint: str, use_cache: bool = True) -> Dict:
    """Fetch data from API endpoint with optional caching.
    
    Args:
        endpoint: API endpoint path
        use_cache: Whether to use cached data if available
        
    Returns:
        JSON response as dictionary
    """
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
    """Fetch travel times from cauldrons to market.
    
    Args:
        cauldron_ids: List of cauldron IDs
        
    Returns:
        Dictionary mapping cauldron_id to travel time in minutes
    """
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
    """Fetch all data from API endpoints.
    
    Returns:
        Dictionary containing all API data:
        - level_data: Potion level measurements
        - tickets: Transport tickets
        - cauldrons: Cauldron information
        - network: Network graph data
        - couriers: Courier information
        - market: Market information
    """
    return {
        'level_data': fetch_api_data('/api/Data/?start_date=0&end_date=2000000000'),
        'tickets': fetch_api_data('/api/Tickets'),
        'cauldrons': fetch_api_data('/api/Information/cauldrons'),
        'network': fetch_api_data('/api/Information/network'),
        'couriers': fetch_api_data('/api/Information/couriers'),
        'market': fetch_api_data('/api/Information/market')
    }

