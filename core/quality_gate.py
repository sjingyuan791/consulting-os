import pandas as pd
from typing import Dict, Any

# Import Rules
from core.quality_rules_financial import (
    check_period_continuity,
    check_negative_values,
    check_balance_sanity,
    detect_yoy_spikes
)
from core.quality_rules_sales import (
    check_required_columns,
    check_date_parse_ratio,
    check_numeric_validity,
    check_duplicate_ratio,
    detect_amount_outliers,
    check_period_coverage
)

def check_financial_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes normalized financial DataFrame for data quality issues.
    Refactored to use modular rules.
    """
    results = {
        "dataset": "financials",
        "quality_score": 100,
        "missing_rate": 0.0,
        "critical_flags": [],
        "warning_flags": [],
        "metrics": {},
        "notes": [],
        "recommended_actions": []
    }

    if df.empty:
        results["quality_score"] = 0
        results["critical_flags"].append("Dataframe is empty")
        return results

    # Run Rules
    rules = [
        check_period_continuity,
        check_negative_values,
        check_balance_sanity,
        detect_yoy_spikes
    ]

    for rule in rules:
        res = rule(df)
        results["quality_score"] += res["score_delta"]
        results["critical_flags"].extend(res["critical_flags"])
        results["warning_flags"].extend(res["warning_flags"])
        results["metrics"].update(res["metrics"])
        results["notes"].extend(res["notes"])

    # Calculate Missing Rate (Common Logic)
    total_expected = len(df.columns) * len(df)
    total_missing = df.isna().sum().sum()
    results["missing_rate"] = round(total_missing / total_expected, 2) if total_expected > 0 else 0
    
    # Cap Score
    results["quality_score"] = max(0, min(100, results["quality_score"]))
    
    # Notes Generation (Summary)
    if results["quality_score"] >= 80:
        results["notes"].append("Data quality is good.")
    elif results["quality_score"] >= 60:
        results["notes"].append("Data has some issues but likely usable.")
    else:
        results["notes"].append("Significant data quality issues detected.")

    return results

def check_sales_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes normalized sales DataFrame for data quality issues.
    Refactored to use modular rules.
    """
    results = {
        "dataset": "sales",
        "quality_score": 100,
        "missing_rate": 0.0,
        "critical_flags": [],
        "warning_flags": [],
        "metrics": {},
        "notes": [],
        "recommended_actions": []
    }

    if df.empty:
        results["quality_score"] = 0
        results["critical_flags"].append("Dataframe is empty")
        return results

    # Run Rules
    rules = [
        check_required_columns,
        check_date_parse_ratio,
        check_numeric_validity,
        check_duplicate_ratio,
        detect_amount_outliers,
        check_period_coverage
    ]

    for rule in rules:
        res = rule(df)
        results["quality_score"] += res["score_delta"]
        results["critical_flags"].extend(res["critical_flags"])
        results["warning_flags"].extend(res["warning_flags"])
        results["metrics"].update(res["metrics"])
        results["notes"].extend(res["notes"])
        
        # Early exit for critical failure (Missing Columns)
        if "data_critical_fail" in res.get("tags", []): # Optional optimization
             pass

    # Calculate Missing Rate
    total_missing = df.isna().sum().sum()
    total_cells = df.size
    results["missing_rate"] = round(total_missing / total_cells, 2) if total_cells > 0 else 0

    # Cap Score
    results["quality_score"] = max(0, min(100, results["quality_score"]))
    
    if results["quality_score"] >= 80:
        results["notes"].append("Sales data looks good.")
    elif results["quality_score"] >= 60:
        results["notes"].append("Sales data acceptable.")
    else:
        results["notes"].append("Sales data has quality concerns.")

    return results
