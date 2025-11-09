# 🧙 Potion Flow Monitoring System

Modular Python system for the Poyo's Potion Factory hackathon challenge.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Analysis

```bash
python3 main.py
```

This will:
- Fetch all data from the API
- Calculate fill rates for each cauldron
- Detect drain events
- Match tickets to drain events
- Identify discrepancies
- Generate analytics reports
- Export CSV files

## 📁 Project Structure

```
.
├── config.py              # Configuration constants
├── api_client.py          # API data fetching
├── data_processor.py      # Data transformation & fill rate calculation
├── drain_detector.py      # Drain event detection algorithm
├── ticket_matcher.py      # Ticket matching & discrepancy detection
├── analytics.py           # Overflow risk & system analytics
├── main.py               # Main runner script
├── requirements.txt      # Python dependencies
└── potion_monitoring.ipynb  # Original analysis notebook
```

## 🔧 Module Overview

### `api_client.py`
Handles all API interactions with caching support:
- Fetches cauldron level data
- Fetches transport tickets
- Fetches cauldron metadata
- Fetches network graph and travel times

### `data_processor.py`
Transforms raw API data into pandas DataFrames:
- Converts timestamps and normalizes JSON
- Calculates fill rates for each cauldron
- Prepares data for analysis

### `drain_detector.py`
Detects potion collection events:
- Rate-of-change based algorithm
- Handles continuous filling during drainage
- Accounts for travel time to market
- Calculates total collected volume

### `ticket_matcher.py`
Matches drain events to transport tickets:
- Dynamic matching by cauldron, date, and volume
- Identifies under-reported, over-reported, and missing tickets
- Configurable tolerance threshold

### `analytics.py`
Provides analytics and forecasting:
- Overflow risk calculation
- Capacity utilization tracking
- System-wide summary statistics
- Suspicious cauldron identification

### `config.py`
Centralized configuration:
```python
BASE_URL = "https://hackutd2025.eog.systems"
MARKET_UNLOAD_TIME_MINUTES = 15
NEGATIVE_RATE_THRESHOLD = -0.05
MIN_DRAIN_VOLUME = 20.0
TICKET_TOLERANCE_PCT = 2.0
```

## 📊 Output Files

| File | Description |
|------|-------------|
| `drain_events.csv` | All detected drain events with volumes and timestamps |
| `ticket_matching.csv` | Ticket matching results with status flags |
| `fill_rates.csv` | Fill rates for each cauldron (per min/hour) |
| `overflow_risk.csv` | Overflow risk analysis for all cauldrons |

## 🎯 Using Modules for Streamlit

Import and use modules directly in your Streamlit app:

```python
from api_client import APIClient
from data_processor import DataProcessor
from drain_detector import DrainDetector
from ticket_matcher import TicketMatcher
from analytics import Analytics

# Fetch data
api_client = APIClient(cache_enabled=True)
raw_data = api_client.fetch_all_data()

# Process
processor = DataProcessor()
df_levels = processor.transform_level_data(raw_data['level_data'])

# Analyze
detector = DrainDetector()
df_drains = detector.detect_all_drains(df_levels, fill_rates, travel_times)

# Match tickets
matcher = TicketMatcher()
df_matched = matcher.match_drains_to_tickets(df_drains, df_tickets)

# Get analytics
analytics = Analytics()
overflow_risk = analytics.calculate_overflow_risk(df_levels, df_cauldrons, df_fill_rates)
```

## 🔬 Key Algorithms

### Fill Rate Calculation
Uses median of positive rate changes during filling periods (robust to outliers):
```python
fill_rate = median(positive_level_changes / time_differences)
```

### Drain Detection
Rate-of-change based detection with continuous filling compensation:
```python
level_drop = level_before - level_after
potion_generated_during_drain = fill_rate * drain_duration
total_collected = level_drop + potion_generated_during_drain
```

### Ticket Matching
Dynamic matching accounting for travel time to market:
```python
ticket_date = drain_end + travel_time_to_market
match = find_ticket_by(cauldron_id, ticket_date, volume)
```

## 🎯 Hackathon Requirements

### ✅ Required Features (Completed)
- Visualization of potion network data (ready for UI)
- Historic data playback (data structured with timestamps)
- Discrepancy detection (under/over-reporting, missing tickets)
- Dynamic ticket matching (handles changing API data)

### 🌟 Bonus Features (Ready to Implement)
- Overflow risk forecasting (analytics.py)
- Route optimization (network graph available)
- Minimum couriers calculation (data prepared)

## 🐛 Troubleshooting

**No drain events detected:**
- Adjust `NEGATIVE_RATE_THRESHOLD` in config.py (try -0.1 for more sensitivity)
- Lower `MIN_DRAIN_VOLUME` (try 10.0)

**High false positive rate:**
- Increase `NEGATIVE_RATE_THRESHOLD` (less negative = stricter)
- Increase `MIN_DRAIN_VOLUME` (higher = only large drains)

**Ticket matching issues:**
- Adjust `TICKET_TOLERANCE_PCT` in config.py
- Check travel time calculations in api_client.py

## 🏆 Next Steps

The data processing pipeline is complete and modular. Focus on:
1. Building Streamlit UI with real-time updates
2. Interactive map visualization (Folium/Plotly)
3. Time-series playback controls
4. Route optimization visualization
5. Alert system for high-risk cauldrons
