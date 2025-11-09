#!/usr/bin/env python3
"""CLI runner script for Potion Flow Monitoring System"""
from backend.api import fetch_all_data, fetch_travel_times
from backend.data_transforms import transform_level_data, transform_tickets, transform_cauldrons, get_cauldron_ids
from backend.fill_rates import calculate_fill_rates
from backend.drain_detection import detect_all_drains, match_drains_to_tickets, get_matching_summary
from backend.analytics import calculate_overflow_risk, get_system_summary, get_overflow_priority
from backend.reporting import get_daily_reconciliation, get_witch_performance, get_suspicious_patterns


def main():
    print("🧙 Potion Flow Monitoring System")
    print("=" * 60)
    
    print("\n⬇ Fetching data from API...")
    raw_data = fetch_all_data()
    
    print("🔄 Processing data...")
    df_levels = transform_level_data(raw_data['level_data'])
    df_tickets = transform_tickets(raw_data['tickets'])
    df_cauldrons = transform_cauldrons(raw_data['cauldrons'])
    df_fill_rates = calculate_fill_rates(df_levels)
    
    fill_rates = dict(zip(df_fill_rates['cauldron'], df_fill_rates['fill_rate_per_min']))
    cauldron_ids = get_cauldron_ids(df_levels)
    travel_times = fetch_travel_times(cauldron_ids)
    
    print(f"✓ Level measurements: {len(df_levels)} records")
    print(f"✓ Transport tickets: {len(df_tickets)} tickets")
    print(f"✓ Cauldrons tracked: {len(df_cauldrons)} cauldrons")
    
    print("\n🔍 Detecting drain events...")
    df_drain_events = detect_all_drains(df_levels, fill_rates, travel_times)
    print(f"✓ Detected {len(df_drain_events)} drain events")
    print(f"  Total collected: {df_drain_events['total_collected'].sum():.2f}L")
    
    print("\n🎫 Matching tickets to drains...")
    df_matched = match_drains_to_tickets(df_drain_events, df_tickets)
    summary = get_matching_summary(df_matched)
    
    print(f"✓ Matched: {summary['matched']}")
    print(f"⚠ Under-reported: {summary['under_reported']}")
    print(f"⚠ No ticket found: {summary['no_ticket']}")
    print(f"  Accuracy: {summary['accuracy_pct']:.1f}%")
    print(f"  Unaccounted volume: {summary['total_unaccounted']:.2f}L")
    
    print("\n📊 Running analytics...")
    df_overflow = calculate_overflow_risk(df_levels, df_cauldrons, df_fill_rates)
    high_risk = df_overflow[df_overflow['risk_level'] == 'HIGH']
    
    if len(high_risk) > 0:
        print(f"⚠ {len(high_risk)} cauldrons at HIGH overflow risk!")
        for _, row in high_risk.iterrows():
            print(f"  - {row['cauldron_id']}: {row['hours_to_overflow']:.1f}h to overflow")
    else:
        print("✓ No immediate overflow risks")
    
    print("\n" + "=" * 60)
    print("SYSTEM SUMMARY")
    print("=" * 60)
    system_summary = get_system_summary(
        df_levels, df_tickets, df_drain_events, df_matched, df_fill_rates, df_overflow
    )
    for key, value in system_summary.items():
        print(f"{key}: {value}")
    
    print("\n📊 Generating advanced analytics...")
    df_reconciliation = get_daily_reconciliation(df_matched, df_tickets)
    df_witch_perf = get_witch_performance(df_matched, df_tickets)
    df_priority = get_overflow_priority(df_overflow, travel_times)
    patterns = get_suspicious_patterns(df_matched)
    
    print(f"✓ Daily reconciliation: {len(df_reconciliation)} records")
    print(f"✓ Witch performance: {len(df_witch_perf)} couriers")
    print(f"✓ Priority ranking: {len(df_priority)} cauldrons")
    print(f"✓ Suspicious patterns: {patterns['missing_tickets']} missing tickets, {patterns['total_unaccounted']:.2f}L unaccounted")
    
    print("\n💾 Exporting results...")
    df_drain_events.to_csv('drain_events.csv', index=False)
    df_matched.to_csv('ticket_matching.csv', index=False)
    df_fill_rates.to_csv('fill_rates.csv', index=False)
    df_overflow.to_csv('overflow_risk.csv', index=False)
    df_reconciliation.to_csv('daily_reconciliation.csv', index=False)
    df_witch_perf.to_csv('witch_performance.csv', index=False)
    df_priority.to_csv('overflow_priority.csv', index=False)
    print("✓ Exported 7 CSV files")
    
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
