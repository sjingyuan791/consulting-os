import pandas as pd
from typing import Dict, List, Any

def init_rule_result() -> Dict[str, Any]:
    return {
        "score_delta": 0,
        "critical_flags": [],
        "warning_flags": [],
        "metrics": {},
        "notes": []
    }

def check_required_columns(df: pd.DataFrame) -> Dict[str, Any]:
    res = init_rule_result()
    required_cols = ["year_month", "amount", "customer"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        res["critical_flags"].append(f"Missing required columns: {', '.join(missing_cols)}")
        res["score_delta"] -= 40
    return res

def check_date_parse_ratio(df: pd.DataFrame) -> Dict[str, Any]:
    res = init_rule_result()
    if "year_month" in df.columns:
        try:
            valid_dates = pd.to_datetime(df["year_month"], errors='coerce').notna().sum()
            ratio = valid_dates / len(df) if len(df) > 0 else 0
            res["metrics"]["date_parse_ratio"] = round(ratio, 2)
            if ratio < 0.9:
                res["critical_flags"].append("High rate of invalid dates in 'year_month'")
                res["score_delta"] -= 20
        except (TypeError, ValueError) as e:
            res["critical_flags"].append("Date parsing failed completely")
            res["score_delta"] -= 20
    return res

def check_numeric_validity(df: pd.DataFrame) -> Dict[str, Any]:
    res = init_rule_result()
    if "amount" in df.columns:
        valid_amounts = pd.to_numeric(df["amount"], errors='coerce').notna().sum()
        ratio = valid_amounts / len(df) if len(df) > 0 else 0
        res["metrics"]["amount_parse_ratio"] = round(ratio, 2)
        if ratio < 0.95:
             res["warning_flags"].append("Some amounts are not numeric")
             res["score_delta"] -= 10
    return res

def check_duplicate_ratio(df: pd.DataFrame) -> Dict[str, Any]:
    res = init_rule_result()
    if not df.empty:
        dups = df.duplicated().sum()
        dup_ratio = dups / len(df)
        res["metrics"]["duplicate_ratio"] = round(dup_ratio, 2)
        if dup_ratio > 0.1:
            res["warning_flags"].append(f"High duplicate rate ({int(dup_ratio*100)}%)")
            res["score_delta"] -= 10
    return res

def detect_amount_outliers(df: pd.DataFrame) -> Dict[str, Any]:
    res = init_rule_result()
    if "amount" in df.columns:
        amounts = pd.to_numeric(df["amount"], errors='coerce').dropna()
        if not amounts.empty:
            q1 = amounts.quantile(0.25)
            q3 = amounts.quantile(0.75)
            iqr = q3 - q1
            upper_bound = q3 + 3 * iqr 
            lower_bound = q1 - 3 * iqr
            outliers = amounts[(amounts > upper_bound) | (amounts < lower_bound)]
            outlier_ratio = len(outliers) / len(amounts)
            
            if outlier_ratio > 0.05:
                res["warning_flags"].append("Detected significant outliers in Amount")
                # No score penalty for now
    return res

def check_period_coverage(df: pd.DataFrame) -> Dict[str, Any]:
    res = init_rule_result()
    if "year_month" in df.columns:
        try:
            dates = pd.to_datetime(df["year_month"], errors='coerce').dropna()
            if not dates.empty:
                min_date = dates.min()
                max_date = dates.max()
                res["metrics"]["period_start"] = min_date.strftime("%Y-%m")
                res["metrics"]["period_end"] = max_date.strftime("%Y-%m")
                months_diff = (max_date.year - min_date.year) * 12 + max_date.month - min_date.month + 1
                unique_months = dates.dt.to_period("M").nunique()
                
                if unique_months < months_diff * 0.8 and months_diff > 3:
                     res["warning_flags"].append("Data might have missing months")
        except (TypeError, ValueError, AttributeError):
            pass  # Silently skip period analysis if data is malformed
    return res
