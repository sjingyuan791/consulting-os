import pandas as pd
from typing import Dict

def analyze_sales(df: pd.DataFrame) -> Dict:
    """
    Analyzes sales detail data.
    Returns:
    - top_customers: List[Dict] with share
    - monthly_trend: List[Dict] (timestamp, total info, rolling_3m, yoy)
    - pareto: Top 20% customers share
    - concentration: top1/3/5 shares
    """
    if df.empty:
        return {}
        
    results = {}
    
    # Ensure amount is numeric
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    
    total_sales = df['amount'].sum()
    
    # 1. Top Customers & Concentration
    cust_group = df.groupby('customer')['amount'].sum().reset_index()
    cust_group = cust_group.sort_values('amount', ascending=False)
    cust_group['share'] = cust_group['amount'] / total_sales if total_sales else 0
    
    # Concentration Metrics
    results['top1_share'] = cust_group.iloc[0]['share'] if len(cust_group) > 0 else 0
    results['top3_share'] = cust_group.head(3)['share'].sum() if len(cust_group) > 0 else 0
    results['top5_share'] = cust_group.head(5)['share'].sum() if len(cust_group) > 0 else 0
    
    results['top_customers'] = cust_group.head(10).to_dict('records')
    
    # Pareto (Share of top 20%)
    n_cust = len(cust_group)
    top_20_n = int(n_cust * 0.2)
    if top_20_n > 0:
        pareto_share = cust_group.head(top_20_n)['amount'].sum() / total_sales if total_sales else 0
    else:
        pareto_share = 1.0 if n_cust > 0 else 0
        
    results['pareto_top_20_share'] = pareto_share
    
    # 2. Monthly Trend (Rolling & YoY)
    try:
        # Create a copy to avoid SettingWithCopy warnings if df is slice
        df = df.copy()
        
        # Parse Dates
        df['dt'] = pd.to_datetime(df['year_month'])
        
        # Group by Month
        monthly = df.groupby(df['dt'].dt.to_period("M"))['amount'].sum().reset_index()
        monthly = monthly.sort_values('dt')
        
        # Convert Period back to timestamp for rolling calc or just use index
        monthly['timestamp'] = monthly['dt'].dt.to_timestamp()
        monthly['year_month'] = monthly['dt'].astype(str)
        
        # Rolling 3M Avg
        monthly['rolling_3m_avg'] = monthly['amount'].rolling(window=3).mean().fillna(0)
        
        # YoY Growth
        # Shift 12 periods if we assume continuous months. 
        # Since group by period("M") might skip months if no data, we should reindex.
        full_idx = pd.period_range(start=monthly['dt'].min(), end=monthly['dt'].max(), freq='M')
        monthly_reindexed = monthly.set_index('dt').reindex(full_idx, fill_value=0).reset_index()
        monthly_reindexed = monthly_reindexed.rename(columns={'index': 'dt'})
        
        monthly_reindexed['yoy_growth'] = monthly_reindexed['amount'].pct_change(periods=12).fillna(0)
        # Recalculate rolling 3m on full index for accuracy
        monthly_reindexed['rolling_3m_avg'] = monthly_reindexed['amount'].rolling(window=3).mean().fillna(0)
        
        # Format back for JSON
        monthly_reindexed['year_month'] = monthly_reindexed['dt'].astype(str)
        # Drop Period index column if exists or just keep needed
        final_cols = ['year_month', 'amount', 'rolling_3m_avg', 'yoy_growth']
        results['monthly_trend'] = monthly_reindexed[final_cols].to_dict('records')
        
    except Exception as e:
        print(f"Monthly Analysis Error: {e}")
        # Fallback
        grouped = df.groupby('year_month')['amount'].sum().reset_index()
        results['monthly_trend'] = grouped.to_dict('records')

    return results
