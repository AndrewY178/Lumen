# 🧙 Potion Flow Monitoring System

Modular Python system for the Poyo's Potion Factory hackathon challenge (HackUTD2025).

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
├── analysis.py            # All data analysis functions
├── app.py                 # Streamlit dashboard
├── main.py                # CLI runner script
├── requirements.txt       # Python dependencies
└── potion_monitoring.ipynb  # Original analysis notebook
```

## 🔧 Module Overview

### `analysis.py`
Consolidated module with all analysis functions:
- **API Functions**: Fetch data from all endpoints with caching
- **Data Processing**: Transform JSON to DataFrames, calculate fill rates
- **Drain Detection**: Rate-of-change algorithm with continuous fill compensation
- **Ticket Matching**: Dynamic matching with discrepancy detection
- **Analytics**: Overflow risk, capacity utilization, system summaries

### `app.py`
Interactive Streamlit dashboard:
- Network map with cauldron and market locations
- Clickable nodes to view individual cauldron details
- Time series plots and rate-of-change visualization
- Real-time statistics and overflow risk indicators

### Configuration
Constants defined in `analysis.py`:
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

## 🎯 Using the Analysis Module

Simple function-based API:

```python
import analysis

# Fetch all data
raw_data = analysis.fetch_all_data()

# Transform data
df_levels = analysis.transform_level_data(raw_data['level_data'])
df_tickets = analysis.transform_tickets(raw_data['tickets'])

# Calculate fill rates and detect drains
df_fill_rates = analysis.calculate_fill_rates(df_levels)
fill_rates = dict(zip(df_fill_rates['cauldron'], df_fill_rates['fill_rate_per_min']))
cauldron_ids = analysis.get_cauldron_ids(df_levels)
travel_times = analysis.fetch_travel_times(cauldron_ids)
df_drains = analysis.detect_all_drains(df_levels, fill_rates, travel_times)

# Match tickets
df_matched = analysis.match_drains_to_tickets(df_drains, df_tickets)

# Get analytics
df_overflow = analysis.calculate_overflow_risk(df_levels, df_cauldrons, df_fill_rates)
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
- Adjust `TICKET_TOLERANCE_PCT` in analysis.py

## 🏆 Next Steps

The data processing pipeline is complete and modular. Focus on:
1. Building Streamlit UI with real-time updates
2. Interactive map visualization (Folium/Plotly)
3. Time-series playback controls
4. Route optimization visualization
5. Alert system for high-risk cauldrons
