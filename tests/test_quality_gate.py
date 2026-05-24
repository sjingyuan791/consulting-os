import pandas as pd
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.quality_gate import check_financial_quality, check_sales_quality

def test_financial_quality():
    print("Testing Financial Quality Gate...")
    
    # Case 1: Perfect Data
    df_good = pd.DataFrame({
        "year": [2023, 2024],
        "sales": [1000, 1100],
        "operating_profit": [100, 110],
        "total_assets": [1000, 1100],
        "net_assets": [500, 600],
        "current_assets": [600, 700],
        "current_liabilities": [300, 350],
        "interest_bearing_debt": [100, 100]
    })
    res = check_financial_quality(df_good)
    print(f"Good Data Score: {res['quality_score']}")
    assert res['quality_score'] >= 80, "Perfect data should have high score"

    # Case 2: Negative Assets
    df_bad = pd.DataFrame({
        "year": [2023],
        "sales": [1000],
        "total_assets": [-100], # Error
        "net_assets": [500],
        "operating_profit": [100]
    })
    res = check_financial_quality(df_bad)
    print(f"Bad Data Score: {res['quality_score']}")
    print(f"Critical Flags: {res['critical_flags']}")
    assert res['quality_score'] < 100, "Should detect negative assets"
    assert any("Negative values" in s for s in res['critical_flags'])

def test_sales_quality():
    print("\nTesting Sales Quality Gate...")
    
    # Case 1: Good Data
    df_good = pd.DataFrame({
        "year_month": ["2024-01", "2024-02"],
        "amount": [1000, 2000],
        "customer": ["A", "B"]
    })
    res = check_sales_quality(df_good)
    print(f"Good Data Score: {res['quality_score']}")
    assert res['quality_score'] >= 80

    # Case 2: Missing Columns
    df_bad = pd.DataFrame({
        "amount": [1000]
    })
    res = check_sales_quality(df_bad)
    print(f"Bad Data Score: {res['quality_score']}")
    print(f"Critical Flags: {res['critical_flags']}")
    assert res['quality_score'] <= 60
    assert any("Missing required columns" in s for s in res['critical_flags'])

if __name__ == "__main__":
    try:
        test_financial_quality()
        test_sales_quality()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        exit(1)
