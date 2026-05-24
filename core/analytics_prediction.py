import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

def calculate_cagr(start_value: float, end_value: float, periods: int) -> float:
    """Calculates Compound Annual Growth Rate."""
    if start_value <= 0 or periods <= 0:
        return 0.0
    return (end_value / start_value) ** (1 / periods) - 1

def predict_future_performance(df_fin: pd.DataFrame, years_to_predict: int = 3) -> pd.DataFrame:
    """
    Generates a forecast for key financial metrics based on historical CAGR and linear trend.
    Assumes df_fin has 'year' and metrics like 'sales', 'operating_profit'.
    """
    if df_fin is None or df_fin.empty or len(df_fin) < 2:
        return pd.DataFrame()

    df_sorted = df_fin.sort_values("year")
    last_year = df_sorted.iloc[-1]["year"]
    
    # Metrics to forecast
    metrics = ["sales", "gross_profit", "operating_profit", "net_income"]
    
    future_data = []
    
    # Simple Logic: Use weighted average growth of last 3 years (or all if <3)
    # Weight recent years higher
    
    for i in range(years_to_predict):
        new_year = last_year + i + 1
        row = {"year": new_year, "type": "forecast"}
        
        for m in metrics:
            if m not in df_sorted.columns:
                continue
            
            # Get historical growth rates
            # Simplified: Just take the last year's growth and dampen it slightly (conservative)
            # Better: Linear Regression if we had sklearn, but sticking to numpy/pandas for MVP robustness
            
            # Linear Trend
            x = df_sorted["year"].values
            y = df_sorted[m].values
            
            # Slope/Intercept
            if len(x) > 1:
                A = np.vstack([x, np.ones(len(x))]).T
                slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
                
                # Predict
                pred = slope * new_year + intercept
                
                # Sanity check: Don't allow negative sales if history was positive
                if y[-1] > 0 and pred < 0:
                    pred = y[-1] * 0.9 # Floor at 10% decline instead of negative
                
                row[m] = pred
            else:
                row[m] = y[0] # Fallback
            
        future_data.append(row)
        
    return pd.DataFrame(future_data)
