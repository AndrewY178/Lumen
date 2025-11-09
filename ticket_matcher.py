import pandas as pd
import config

class TicketMatcher:
    @staticmethod
    def match_drains_to_tickets(df_drains: pd.DataFrame, df_tickets: pd.DataFrame, 
                                tolerance_pct: float = None) -> pd.DataFrame:
        if tolerance_pct is None:
            tolerance_pct = config.TICKET_TOLERANCE_PCT
        
        results = []
        
        for _, drain in df_drains.iterrows():
            ticket_date = drain.get('ticket_date', drain['date'])
            cauldron_id = drain['cauldron_id']
            drain_amount = drain['total_collected']
            
            matching_tickets = df_tickets[
                (df_tickets['cauldron_id'] == cauldron_id) & 
                (df_tickets['date'].dt.date == ticket_date)
            ]
            
            if len(matching_tickets) == 0:
                results.append({
                    'drain_id': f"{cauldron_id}_{drain['end_time']}",
                    'cauldron_id': cauldron_id,
                    'drain_date': drain['date'],
                    'ticket_date': ticket_date,
                    'drain_time': drain['end_time'],
                    'drain_amount': drain_amount,
                    'ticket_id': None,
                    'ticket_amount': None,
                    'difference': None,
                    'difference_pct': None,
                    'status': 'NO_TICKET_FOUND',
                    'notes': 'Drain event detected but no ticket reported'
                })
            else:
                best_ticket = None
                min_diff = float('inf')
                
                for _, ticket in matching_tickets.iterrows():
                    diff = abs(drain_amount - ticket['amount_collected'])
                    if diff < min_diff:
                        min_diff = diff
                        best_ticket = ticket
                
                ticket_amount = best_ticket['amount_collected']
                pct_diff = (min_diff / drain_amount) * 100 if drain_amount > 0 else 0
                
                if abs(pct_diff) <= tolerance_pct:
                    status = 'MATCHED'
                    notes = f'Match (diff: {pct_diff:.2f}%)'
                elif ticket_amount < drain_amount:
                    under_reported = drain_amount - ticket_amount
                    status = 'UNDER_REPORTED'
                    notes = f'Under by {under_reported:.2f}L ({pct_diff:.2f}%)'
                else:
                    over_reported = ticket_amount - drain_amount
                    status = 'OVER_REPORTED'
                    notes = f'Over by {over_reported:.2f}L ({pct_diff:.2f}%)'
                
                results.append({
                    'drain_id': f"{cauldron_id}_{drain['end_time']}",
                    'cauldron_id': cauldron_id,
                    'drain_date': drain['date'],
                    'ticket_date': ticket_date,
                    'drain_time': drain['end_time'],
                    'drain_amount': drain_amount,
                    'ticket_id': best_ticket['ticket_id'],
                    'ticket_amount': ticket_amount,
                    'difference': ticket_amount - drain_amount,
                    'difference_pct': pct_diff,
                    'status': status,
                    'notes': notes
                })
        
        return pd.DataFrame(results)
    
    @staticmethod
    def get_summary(df_matched: pd.DataFrame) -> dict:
        if len(df_matched) == 0:
            return {}
        
        total_drained = df_matched['drain_amount'].sum()
        total_ticketed = df_matched[df_matched['ticket_amount'].notna()]['ticket_amount'].sum()
        
        return {
            'total_drains': len(df_matched),
            'matched': len(df_matched[df_matched['status'] == 'MATCHED']),
            'under_reported': len(df_matched[df_matched['status'] == 'UNDER_REPORTED']),
            'over_reported': len(df_matched[df_matched['status'] == 'OVER_REPORTED']),
            'no_ticket': len(df_matched[df_matched['status'] == 'NO_TICKET_FOUND']),
            'total_drained_volume': total_drained,
            'total_ticketed_volume': total_ticketed,
            'total_unaccounted': total_drained - total_ticketed,
            'accuracy_pct': (len(df_matched[df_matched['status'] == 'MATCHED']) / len(df_matched)) * 100
        }

