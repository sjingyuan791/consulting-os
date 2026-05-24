"""
Pytest Configuration and Shared Fixtures.
テスト共通設定・フィクスチャ
"""
import pytest
import pandas as pd
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import date

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



# ==========================================
# 財務データフィクスチャ
# ==========================================

@pytest.fixture
def sample_financial_data():
    """3年分の財務データサンプル"""
    return pd.DataFrame({
        "year": [2022, 2023, 2024],
        "sales": [100_000_000, 110_000_000, 120_000_000],
        "gross_profit": [40_000_000, 44_000_000, 48_000_000],
        "operating_profit": [10_000_000, 11_000_000, 12_000_000],
        "ordinary_profit": [9_000_000, 10_000_000, 11_000_000],
        "net_income": [6_000_000, 7_000_000, 8_000_000],
        "total_assets": [80_000_000, 85_000_000, 90_000_000],
        "net_assets": [30_000_000, 35_000_000, 40_000_000],
        "current_assets": [40_000_000, 42_000_000, 45_000_000],
        "current_liabilities": [25_000_000, 26_000_000, 27_000_000],
        "cash_and_equivalents": [15_000_000, 18_000_000, 20_000_000],
        "interest_bearing_debt": [20_000_000, 18_000_000, 15_000_000],
    })


@pytest.fixture
def sample_source_data():
    """AI検証用ソースデータ"""
    return {
        "roa": 3.2,
        "roe": 8.5,
        "revenue": 100_000_000,
        "operating_profit": 5_000_000,
        "net_income": 3_000_000,
        "total_assets": 80_000_000,
        "net_assets": 35_000_000,
        "売上高": 100_000_000,
        "営業利益": 5_000_000,
        "純資産": 35_000_000,
        "原価率": 0.72,
        "粗利率": 0.28,
    }


# ==========================================
# 施策データフィクスチャ
# ==========================================

@pytest.fixture
def sample_sales_initiative():
    """売上向上施策サンプル"""
    from core.initiative_impact_model import InitiativeInput, InitiativeType, ConfidenceLevel
    
    return InitiativeInput(
        id="init_001",
        name="新規顧客開拓",
        description="展示会出展による新規顧客獲得",
        initiative_type=InitiativeType.NEW_CUSTOMER,
        confidence=ConfidenceLevel.MEDIUM,
        implementation_months=6,
        target_customers=50,
        conversion_rate=0.10,
        unit_price=500_000,
        margin_rate=0.30,
    )


@pytest.fixture
def sample_cost_initiative():
    """コスト削減施策サンプル"""
    from core.initiative_impact_model import InitiativeInput, InitiativeType, ConfidenceLevel
    
    return InitiativeInput(
        id="init_002",
        name="仕入先見直し",
        description="既存仕入先との価格交渉",
        initiative_type=InitiativeType.COST_VARIABLE,
        confidence=ConfidenceLevel.HIGH,
        implementation_months=3,
        current_cost=30_000_000,
        reduction_rate=0.05,
    )


@pytest.fixture
def sample_investment_initiative():
    """投資施策サンプル"""
    from core.initiative_impact_model import InitiativeInput, InitiativeType, ConfidenceLevel
    
    return InitiativeInput(
        id="init_003",
        name="生産設備更新",
        description="老朽化設備の更新による生産性向上",
        initiative_type=InitiativeType.INVESTMENT,
        confidence=ConfidenceLevel.MEDIUM,
        implementation_months=12,
        initial_investment=10_000_000,
        annual_benefit=3_000_000,
        useful_life_years=5,
    )


# ==========================================
# 借入データフィクスチャ
# ==========================================

@pytest.fixture
def sample_loan_data():
    """借入データサンプル"""
    return {
        "bank_name": "〇〇銀行",
        "current_balance": 50_000_000,
        "interest_rate": 0.015,
        "maturity_date": "2030-03",
        "start_month": "2024-04",
        "repayment_method": "equal_principal",
    }


# ==========================================
# モックフィクスチャ
# ==========================================

@pytest.fixture
def mock_supabase():
    """Supabaseモック"""
    mock = MagicMock()
    mock.table.return_value.select.return_value.execute.return_value.data = []
    mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-id"}]
    return mock


@pytest.fixture
def mock_llm_response():
    """LLMレスポンスモック"""
    return {
        "chat_response": "分析結果をお伝えします。",
        "hypotheses": ["仮説1", "仮説2"],
        "confidence": 0.8,
    }


# ==========================================
# 共通ヘルパー
# ==========================================

def assert_positive(value, name="value"):
    """正の値であることを確認"""
    assert value >= 0, f"{name} should be positive, got {value}"


def assert_in_range(value, min_val, max_val, name="value"):
    """範囲内であることを確認"""
    assert min_val <= value <= max_val, f"{name} should be in [{min_val}, {max_val}], got {value}"
