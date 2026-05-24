import pandas as pd
from typing import List, Dict

from core.models import FinancialMetrics

def calculate_financial_metrics(df: pd.DataFrame) -> List[FinancialMetrics]:
    """
    Calculates key financial ratios from normalized DataFrame.
    Returns a list of FinancialMetrics objects (one per year).
    """
    if df.empty:
        return []

    # Sort by year
    if 'year' in df.columns:
        df = df.sort_values('year')
    
    # Ensure numeric columns
    cols_to_numeric = ['sales', 'gross_profit', 'operating_profit', 'net_income', 
                       'total_assets', 'net_assets', 'current_assets', 
                       'current_liabilities', 'interest_bearing_debt']
    for col in cols_to_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    metrics = []
    
    # Pre-calculate growth using pandas pct_change
    if 'sales' in df.columns:
        df['sales_growth'] = df['sales'].pct_change().fillna(0)
    else:
        df['sales_growth'] = 0

    for i, row in df.iterrows():
        # Raw Data (Required for ROA Tree/CF)
        sales = row.get('sales', 0)
        gp = row.get('gross_profit', 0)
        op = row.get('operating_profit', 0)
        net_income = row.get('net_income', 0)
        
        total_assets = row.get('total_assets', 0)
        net_assets = row.get('net_assets', 0) # Equity
        curr_assets = row.get('current_assets', 0)
        curr_liab = row.get('current_liabilities', 0)
        debt = row.get('interest_bearing_debt', 0)
        
        # Ratios
        gross_profit_margin = gp / sales if sales else 0
        operating_profit_margin = op / sales if sales else 0
        net_profit_margin = net_income / sales if sales else 0
        
        roa = net_income / total_assets if total_assets else 0
        roe = net_income / net_assets if net_assets else 0
        
        equity_ratio = net_assets / total_assets if total_assets else 0
        current_ratio = curr_assets / curr_liab if curr_liab else 0
        debt_equity_ratio = debt / net_assets if net_assets else 0
        
        sales_growth = row.get('sales_growth', 0)
        
        m = FinancialMetrics(
            year=int(row.get('year', 0)),
            sales_growth=sales_growth,
            gross_profit_margin=gross_profit_margin,
            operating_profit_margin=operating_profit_margin,
            roa=roa,
            equity_ratio=equity_ratio,
            current_ratio=current_ratio,
            debt_equity_ratio=debt_equity_ratio
        )
        
        metrics.append(m)

    return metrics
