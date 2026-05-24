import pandas as pd
import numpy as np
from typing import Dict, List, Any

def init_rule_result() -> Dict[str, Any]:
    return {
        "score_delta": 0,
        "critical_flags": [],
        "warning_flags": [],
        "metrics": {},
        "notes": []
    }

def check_period_continuity(df: pd.DataFrame) -> Dict[str, Any]:
    res = init_rule_result()
    if "year" in df.columns:
        years = df["year"].sort_values().unique()
        res["metrics"]["years_count"] = len(years)
        res["metrics"]["year_range"] = f"{int(min(years))}-{int(max(years))}"
        
        if len(df) > len(years):
            res["critical_flags"].append("Duplicate years found")
            res["score_delta"] -= 20
        
        if len(years) > 1:
            diffs = np.diff(years)
            if not all(d == 1 for d in diffs):
                res["warning_flags"].append("Years are not continuous")
                res["score_delta"] -= 10
    else:
        res["critical_flags"].append("Missing 'year' column")
        res["score_delta"] -= 30
    return res

def check_negative_values(df: pd.DataFrame) -> Dict[str, Any]:
    res = init_rule_result()
    non_negative_cols = ["sales", "total_assets", "current_assets", "current_liabilities", "interest_bearing_debt"]
    for col in non_negative_cols:
        if col in df.columns and (df[col] < 0).any():
            res["critical_flags"].append(f"Negative values found in {col}")
            res["score_delta"] -= 15
    return res

def check_balance_sanity(df: pd.DataFrame) -> Dict[str, Any]:
    res = init_rule_result()
    if "net_assets" in df.columns and "total_assets" in df.columns:
        invalid_rows = df[df["net_assets"] > df["total_assets"] * 1.01]
        if not invalid_rows.empty:
            res["critical_flags"].append("Net Assets > Total Assets in some years")
            res["score_delta"] -= 10
            
    if "sales" in df.columns:
        profit_cols = ["operating_profit", "ordinary_profit", "net_income"]
        for p_col in profit_cols:
            if p_col in df.columns:
                suspicious = df[(df["sales"] == 0) & (df[p_col] != 0)]
                if not suspicious.empty:
                    res["warning_flags"].append(f"Sales is 0 but {p_col} is not 0")
                    res["score_delta"] -= 5
    return res

def detect_yoy_spikes(df: pd.DataFrame) -> Dict[str, Any]:
    res = init_rule_result()
    if "year" in df.columns and len(df) > 1:
        df_sorted = df.sort_values("year")
        cols_to_check = ["sales", "operating_profit"]
        for col in cols_to_check:
            if col in df.columns:
                values = df_sorted[col].values
                for i in range(1, len(values)):
                    prev = values[i-1]
                    curr = values[i]
                    if prev == 0:
                        continue 
                    
                    change_rate = abs((curr - prev) / abs(prev))
                    if change_rate > 2.0:
                        res["warning_flags"].append(f"Extreme YoY change in {col} ({df_sorted['year'].iloc[i]})")
                        res["score_delta"] -= 5
    return res
