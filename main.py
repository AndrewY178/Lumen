#!/usr/bin/env python3
"""
Potion Flow Monitoring System - Main Runner
"""
import pandas as pd
from api_client import APIClient
from data_processor import DataProcessor
from drain_detector import DrainDetector
from ticket_matcher import TicketMatcher
from analytics import Analytics

def main():
    print("🧙 Potion Flow Monitoring System")
    print("=" * 60)
    
    # Fetch data
    print("\n⬇ Fetching data from API...")
    api_client = APIClient(cache_enabled=True)
    raw_data = api_client.fetch_all_data()
    
    # Transform data
    print("🔄 Processing data...")
    processor = DataProcessor()
    df_levels = processor.transform_level_data(raw_data['level_data'])
    df_tickets = processor.transform_tickets(raw_data['tickets'])
    df_cauldrons = processor.transform_cauldrons(raw_data['cauldrons'])
    
    # Calculate fill rates
    df_fill_rates = processor.calculate_fill_rates(df_levels)
    fill_rates = dict(zip(df_fill_rates['cauldron'], df_fill_rates['fill_rate_per_min']))
    
    # Fetch travel times
    cauldron_ids = processor.get_cauldron_ids(df_levels)
    travel_times = api_client.fetch_travel_times(cauldron_ids)
    
    print(f"✓ Level measurements: {len(df_levels)} records")
    print(f"✓ Transport tickets: {len(df_tickets)} tickets")
    print(f"✓ Cauldrons tracked: {len(df_cauldrons)} cauldrons")
    
    # Detect drain events
    print("\n🔍 Detecting drain events...")
    detector = DrainDetector()
    df_drain_events = detector.detect_all_drains(df_levels, fill_rates, travel_times)
    print(f"✓ Detected {len(df_drain_events)} drain events")
    print(f"  Total collected: {df_drain_events['total_collected'].sum():.2f}L")
    
    # Match tickets to drains
    print("\n🎫 Matching tickets to drains...")
    matcher = TicketMatcher()
    df_matched = matcher.match_drains_to_tickets(df_drain_events, df_tickets)
    summary = matcher.get_summary(df_matched)
    
    print(f"✓ Matched: {summary['matched']}")
    print(f"⚠ Under-reported: {summary['under_reported']}")
    print(f"⚠ No ticket found: {summary['no_ticket']}")
    print(f"  Accuracy: {summary['accuracy_pct']:.1f}%")
    print(f"  Unaccounted volume: {summary['total_unaccounted']:.2f}L")
    
    # Analytics
    print("\n📊 Running analytics...")
    analytics = Analytics()
    df_overflow = analytics.calculate_overflow_risk(df_levels, df_cauldrons, df_fill_rates)
    high_risk = df_overflow[df_overflow['risk_level'] == 'HIGH']
    
    if len(high_risk) > 0:
        print(f"⚠ {len(high_risk)} cauldrons at HIGH overflow risk!")
        for _, row in high_risk.iterrows():
            print(f"  - {row['cauldron_id']}: {row['hours_to_overflow']:.1f}h to overflow")
    else:
        print("✓ No immediate overflow risks")
    
    # System summary
    print("\n" + "=" * 60)
    print("SYSTEM SUMMARY")
    print("=" * 60)
    system_summary = analytics.get_system_summary(
        df_levels, df_tickets, df_drain_events, df_matched, df_fill_rates, df_overflow
    )
    for key, value in system_summary.items():
        print(f"{key}: {value}")
    
    # Export results
    print("\n💾 Exporting results...")
    df_drain_events.to_csv('drain_events.csv', index=False)
    df_matched.to_csv('ticket_matching.csv', index=False)
    df_fill_rates.to_csv('fill_rates.csv', index=False)
    df_overflow.to_csv('overflow_risk.csv', index=False)
    print("✓ Exported: drain_events.csv, ticket_matching.csv, fill_rates.csv, overflow_risk.csv")
    
    print("\n✨ Analysis complete!")
    
    return {
        'levels': df_levels,
        'tickets': df_tickets,
        'cauldrons': df_cauldrons,
        'drain_events': df_drain_events,
        'matched': df_matched,
        'fill_rates': df_fill_rates,
        'overflow': df_overflow,
        'travel_times': travel_times
    }

if __name__ == "__main__":
    results = main()

