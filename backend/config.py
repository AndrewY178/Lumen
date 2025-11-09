# Configuration constants for Potion Flow Monitoring System

# API Configuration
BASE_URL = "https://hackutd2025.eog.systems"
MARKET_UNLOAD_TIME = 15  # minutes

# Drain Detection Thresholds
NEGATIVE_RATE_THRESHOLD = -0.05  # L/min threshold for detecting drains
MIN_DRAIN_VOLUME = 20.0  # Minimum volume drop (L) to consider a drain event

# Ticket Matching Tolerance
TICKET_TOLERANCE_PCT = 2.0  # Percentage tolerance for ticket matching

