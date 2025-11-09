import requests
from typing import Dict, List
import config

class APIClient:
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self.data_cache = {}
    
    def fetch_api_data(self, endpoint: str, use_cache: bool = True) -> Dict:
        cache_key = endpoint
        if use_cache and cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        url = f"{config.BASE_URL}{endpoint}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            if self.cache_enabled:
                self.data_cache[cache_key] = data
            return data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {endpoint}: {e}")
            return {}
    
    def fetch_travel_times(self, cauldron_ids: List[str]) -> Dict[str, float]:
        travel_times = {}
        for cauldron_id in cauldron_ids:
            neighbors = self.fetch_api_data(f'/api/Information/graph/neighbors/{cauldron_id}')
            if isinstance(neighbors, list):
                for neighbor in neighbors:
                    if neighbor.get('to', '').startswith('market'):
                        cost_str = neighbor.get('cost', '00:00:00')
                        time_parts = cost_str.split(':')
                        if len(time_parts) == 3:
                            hours, minutes, seconds = int(time_parts[0]), int(time_parts[1]), int(time_parts[2])
                            travel_times[cauldron_id] = hours * 60 + minutes + seconds / 60
                            break
        return travel_times
    
    def fetch_all_data(self) -> Dict:
        return {
            'level_data': self.fetch_api_data('/api/Data/?start_date=0&end_date=2000000000'),
            'tickets': self.fetch_api_data('/api/Tickets'),
            'cauldrons': self.fetch_api_data('/api/Information/cauldrons'),
            'network': self.fetch_api_data('/api/Information/network'),
            'couriers': self.fetch_api_data('/api/Information/couriers'),
            'market': self.fetch_api_data('/api/Information/market')
        }

