# 🧙 Potion Flow Monitoring System

Modular Python system for the Poyo's Potion Factory hackathon challenge (HackUTD2025).

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Analysis

**CLI Mode:**
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

**Interactive Dashboard:**
```bash
# Recommended: Use the run script (handles paths automatically)
python3 run_app.py

# Alternative: Run directly (must be from project root directory)
cd /path/to/Lumen
streamlit run frontend/app.py
```

This will launch the interactive Streamlit dashboard with:
- Network map visualization
- Real-time metrics and statistics
- Ticket validation interface
- Witch performance scorecards
- Overflow priority rankings
- Detailed cauldron analysis

## 📁 Project Structure

```
.
├── backend/               # Data processing and analysis
│   ├── config.py         # Configuration constants
│   ├── api.py            # API data fetching
│   ├── data_transforms.py # Data transformation
│   ├── fill_rates.py     # Fill rate calculations
│   ├── drain_detection.py # Drain detection and matching
│   ├── analytics.py      # Analytics and risk calculations
│   └── reporting.py      # Reporting and performance metrics
│
├── frontend/              # UI and visualization
│   ├── app.py            # Streamlit dashboard
│   ├── visualizations.py # Plotting functions
│   └── data_loader.py    # Streamlit data loading
│
├── main.py               # CLI runner script
├── run_app.py            # Entry point for Streamlit app
├── requirements.txt      # Python dependencies
└── potion_monitoring.ipynb # Original analysis notebook
```

## 🔧 Module Overview

### Backend Modules (`backend/`)
- **`config.py`**: Configuration constants (BASE_URL, thresholds)
- **`api.py`**: API data fetching with caching
- **`data_transforms.py`**: Transform JSON to DataFrames
- **`fill_rates.py`**: Calculate fill rates for cauldrons
- **`drain_detection.py`**: Drain event detection and ticket matching
- **`analytics.py`**: Overflow risk and analytics calculations
- **`reporting.py`**: Reporting and performance metrics

### Frontend Modules (`frontend/`)
- **`app.py`**: Main Streamlit dashboard
- **`visualizations.py`**: Plotting functions for charts and maps
- **`data_loader.py`**: Streamlit data loading with caching

### Configuration
Constants defined in `backend/config.py`:
```python
BASE_URL = "https://hackutd2025.eog.systems"
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

## 🎯 Using the Analysis Modules

Simple function-based API:

```python
from backend.api import fetch_all_data, fetch_travel_times
from backend.data_transforms import transform_level_data, transform_tickets, transform_cauldrons, get_cauldron_ids
from backend.fill_rates import calculate_fill_rates
from backend.drain_detection import detect_all_drains, match_drains_to_tickets
from backend.analytics import calculate_overflow_risk

# Fetch all data
raw_data = fetch_all_data()

# Transform data
df_levels = transform_level_data(raw_data['level_data'])
df_tickets = transform_tickets(raw_data['tickets'])
df_cauldrons = transform_cauldrons(raw_data['cauldrons'])

# Calculate fill rates and detect drains
df_fill_rates = calculate_fill_rates(df_levels)
fill_rates = dict(zip(df_fill_rates['cauldron'], df_fill_rates['fill_rate_per_min']))
cauldron_ids = get_cauldron_ids(df_levels)
travel_times = fetch_travel_times(cauldron_ids)
df_drains = detect_all_drains(df_levels, fill_rates, travel_times)

# Match tickets
df_matched = match_drains_to_tickets(df_drains, df_tickets)

# Get analytics
df_overflow = calculate_overflow_risk(df_levels, df_cauldrons, df_fill_rates)
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
- Adjust `NEGATIVE_RATE_THRESHOLD` in analysis.py (try -0.1 for more sensitivity)
- Lower `MIN_DRAIN_VOLUME` (try 10.0)

**High false positive rate:**
- Increase `NEGATIVE_RATE_THRESHOLD` (less negative = stricter)
- Increase `MIN_DRAIN_VOLUME` (higher = only large drains)

**Ticket matching issues:**
- Adjust `TICKET_TOLERANCE_PCT` in `backend/config.py`

## 🏆 Next Steps

The data processing pipeline is complete and modular. Focus on:
1. Building Streamlit UI with real-time updates
2. Interactive map visualization (Folium/Plotly)
3. Time-series playback controls
4. Route optimization visualization
5. Alert system for high-risk cauldrons
