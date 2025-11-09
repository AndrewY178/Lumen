import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style('darkgrid')

class Visualizer:
    @staticmethod
    def plot_cauldron_levels(df_levels: pd.DataFrame, cauldron_cols: list, figsize=(15, 10)):
        """Plot time series for all cauldrons"""
        n_cauldrons = len(cauldron_cols)
        n_cols = 3
        n_rows = (n_cauldrons + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        axes = axes.flatten() if n_cauldrons > 1 else [axes]
        
        for idx, col in enumerate(cauldron_cols):
            ax = axes[idx]
            df_levels[col].plot(ax=ax, linewidth=1)
            cauldron_id = col.replace('cauldron_levels.', '')
            ax.set_title(cauldron_id, fontweight='bold')
            ax.set_ylabel('Level (L)')
            ax.grid(True, alpha=0.3)
        
        for idx in range(len(cauldron_cols), len(axes)):
            axes[idx].set_visible(False)
        
        plt.tight_layout()
        return fig
    
    @staticmethod
    def plot_fill_rates(df_fill_rates: pd.DataFrame, figsize=(12, 6)):
        """Bar chart of fill rates by cauldron"""
        fig, ax = plt.subplots(figsize=figsize)
        df_sorted = df_fill_rates.sort_values('fill_rate_per_hour')
        ax.barh(df_sorted['cauldron'], df_sorted['fill_rate_per_hour'])
        ax.set_xlabel('Fill Rate (L/hour)', fontsize=12)
        ax.set_ylabel('Cauldron', fontsize=12)
        ax.set_title('Fill Rates by Cauldron', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        return fig
    
    @staticmethod
    def plot_ticket_status(df_matched: pd.DataFrame, figsize=(14, 5)):
        """Pie and bar charts of ticket matching status"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        status_counts = df_matched['status'].value_counts()
        colors = {
            'MATCHED': 'green',
            'UNDER_REPORTED': 'gold',
            'OVER_REPORTED': 'orange',
            'NO_TICKET_FOUND': 'red'
        }
        status_colors = [colors.get(status, 'gray') for status in status_counts.index]
        
        # Bar chart
        ax1.bar(status_counts.index, status_counts.values, color=status_colors)
        ax1.set_ylabel('Count', fontsize=12)
        ax1.set_title('Ticket Status Distribution', fontsize=14, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        
        # Pie chart
        ax2.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%',
                colors=status_colors, startangle=90)
        ax2.set_title('Ticket Status Proportion', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        return fig
    
    @staticmethod
    def plot_drains_vs_tickets(df_levels: pd.DataFrame, df_tickets: pd.DataFrame, 
                               df_drain_events: pd.DataFrame, df_matched: pd.DataFrame,
                               figsize=(20, 16)):
        """Color-coded drain events vs tickets by cauldron"""
        cauldron_ids = sorted(df_tickets['cauldron_id'].unique())
        n_cauldrons = len(cauldron_ids)
        n_cols = 3
        n_rows = (n_cauldrons + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        axes = axes.flatten()
        
        status_colors = {
            'MATCHED': 'green',
            'UNDER_REPORTED': 'gold',
            'OVER_REPORTED': 'orange',
            'NO_TICKET_FOUND': 'red'
        }
        
        for idx, cauldron_id in enumerate(cauldron_ids):
            if idx >= len(axes):
                break
            
            ax = axes[idx]
            
            # Plot tickets
            cauldron_tickets = df_tickets[df_tickets['cauldron_id'] == cauldron_id].sort_values('date')
            if len(cauldron_tickets) > 0:
                ticket_dates = pd.to_datetime(cauldron_tickets['date'])
                ticket_amounts = cauldron_tickets['amount_collected']
                ax.scatter(ticket_dates, ticket_amounts, color='red', marker='o', 
                          s=100, alpha=0.7, label=f'Tickets ({len(cauldron_tickets)})', zorder=3)
            
            # Plot drain events with status colors
            cauldron_matches = df_matched[df_matched['cauldron_id'] == cauldron_id].sort_values('drain_time')
            if len(cauldron_matches) > 0:
                for status, color in status_colors.items():
                    status_drains = cauldron_matches[cauldron_matches['status'] == status]
                    if len(status_drains) > 0:
                        drain_dates = pd.to_datetime(status_drains['drain_time'])
                        drain_amounts = status_drains['drain_amount']
                        ax.scatter(drain_dates, drain_amounts, color=color, marker='s', 
                                  s=100, alpha=0.7, label=f'{status.replace("_", " ").title()} ({len(status_drains)})', 
                                  zorder=2, edgecolors='black', linewidths=0.5)
            
            ax.set_title(cauldron_id, fontsize=11, fontweight='bold')
            ax.set_xlabel('Date', fontsize=9)
            ax.set_ylabel('Volume (L)', fontsize=9)
            ax.legend(fontsize=7, loc='best')
            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=8)
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        for idx in range(len(cauldron_ids), len(axes)):
            axes[idx].set_visible(False)
        
        plt.tight_layout()
        plt.suptitle('Color-Coded Drain Events vs Tickets by Cauldron', 
                     fontsize=14, fontweight='bold', y=1.001)
        return fig
    
    @staticmethod
    def plot_overflow_risk(df_overflow: pd.DataFrame, figsize=(12, 6)):
        """Bar chart of hours to overflow with risk level colors"""
        fig, ax = plt.subplots(figsize=figsize)
        df_sorted = df_overflow.sort_values('hours_to_overflow')
        
        colors = df_sorted['risk_level'].map({
            'HIGH': 'red',
            'MEDIUM': 'orange',
            'LOW': 'green'
        })
        
        ax.barh(df_sorted['cauldron_id'], df_sorted['hours_to_overflow'], color=colors)
        ax.set_xlabel('Hours to Overflow', fontsize=12)
        ax.set_ylabel('Cauldron', fontsize=12)
        ax.set_title('Overflow Risk Analysis', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        ax.axvline(x=12, color='red', linestyle='--', alpha=0.5, label='High Risk Threshold')
        ax.axvline(x=24, color='orange', linestyle='--', alpha=0.5, label='Medium Risk Threshold')
        ax.legend()
        plt.tight_layout()
        return fig

