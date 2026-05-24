import pandas as pd
import numpy as np

# Column Mappings (Japanese -> Standard English)
FINANCIAL_MAP = {
    "sales": ["売上", "売上高", "年商"],
    "cost_of_goods_sold": ["売上原価", "原価", "製造原価", "仕入高"],
    "gross_profit": ["売上総利益", "粗利", "粗利益"],
    "sga_expense": ["販管費", "販売費及び一般管理費", "販売管理費"],
    "operating_profit": ["営業利益"],
    "ordinary_profit": ["経常利益"],
    "net_income": ["当期純利益", "純利益", "税引後利益"],
    "depreciation": ["減価償却費"],
    "interest_expense": ["支払利息", "利息"],
    "total_assets": ["総資産", "資産合計"],
    "net_assets": ["純資産", "純資産合計", "自己資本"],
    "current_assets": ["流動資産"],
    "current_liabilities": ["流動負債"],
    "cash_and_equivalents": ["現預金", "現金及び預金", "キャッシュ"],
    "receivables": ["売掛金", "受取手形", "売掛金及び受取手形"],
    "inventory": ["棚卸資産", "在庫", "商品"],
    "fixed_assets": ["固定資産", "有形固定資産"],
    "long_term_debt": ["長期借入金", "固定負債"],
    "interest_bearing_debt": ["有利子負債", "借入金計", "借入金", "有利子負債合計"],
    "payables": ["買掛金", "支払手形", "買入債務"],
    "personnel_cost": ["人件費", "給与手当", "労務費"],
    "employee_count": ["従業員数", "社員数", "人員"],
    "annual_repayment": ["年間返済額", "元金返済額", "借入金返済額"]
}

SALES_MAP = {
    "year_month": ["年月", "売上月", "Date"],
    "customer": ["得意先", "顧客名", "取引先"],
    "product": ["商品名", "品目"],
    "amount": ["金額", "売上金額"],
    "quantity": ["数量", "個数"]
}

def normalize_columns(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Renames columns based on the mapping dictionary."""
    new_cols = {}
    for standard, candidates in mapping.items():
        found = False
        for c in candidates:
            if c in df.columns:
                new_cols[c] = standard
                found = True
                break
        if not found and standard not in df.columns:
            # Keep track of missing? For now just skip
            pass
            
    return df.rename(columns=new_cols)

def clean_financial_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizes financial data (Yearly PL/BS)."""
    df = normalize_columns(df, FINANCIAL_MAP)
    # Ensure all standard columns exist (fill 0 if missing)
    for col in FINANCIAL_MAP.keys():
        if col not in df.columns:
            df[col] = 0

    # Ensure numeric
    numeric_cols = list(FINANCIAL_MAP.keys())
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Year column normalization
    if "年度" in df.columns:
        df = df.rename(columns={"年度": "year"})
    elif "Year" in df.columns:
        df = df.rename(columns={"Year": "year"})
    
    # --- Auto-calculate gross_profit if missing ---
    if "gross_profit" not in df.columns or (df["gross_profit"] == 0).all():
        if "sales" in df.columns and "cost_of_goods_sold" in df.columns:
            df["gross_profit"] = df["sales"] - df["cost_of_goods_sold"]
        elif "sales" in df.columns and "operating_profit" in df.columns and "sga_expense" in df.columns:
            # gross_profit = operating_profit + sga_expense
            df["gross_profit"] = df["operating_profit"] + df["sga_expense"]
    
    # --- Auto-calculate cost_of_goods_sold if missing ---
    if "cost_of_goods_sold" not in df.columns or (df["cost_of_goods_sold"] == 0).all():
        if "sales" in df.columns and "gross_profit" in df.columns and not (df["gross_profit"] == 0).all():
            df["cost_of_goods_sold"] = df["sales"] - df["gross_profit"]
        
    return df

def clean_sales_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizes detail sales transaction data."""
    df = normalize_columns(df, SALES_MAP)
    return df
