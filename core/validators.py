import pandas as pd
from typing import List, Tuple

def validate_financial_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Checks if essential financial columns exist."""
    required = ["sales", "operating_profit", "year"]
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        return False, [f"Missing columns: {', '.join(missing)}"]
    return True, []

def validate_sales_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Checks if sales log columns exist."""
    required = ["customer", "amount"] # Minimal
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        return False, [f"Missing columns: {', '.join(missing)}"]
    return True, []
