"""
Test Cashflow Engine.
キャッシュフローエンジンのテスト
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.cashflow_engine import (
    CashFlowEngine, CashFlowStatement, CashFlowMetrics,
    SimpleCashFlow, SimpleCashFlowOutput,
    calculate_simple_cf, calculate_simple_cf_from_data
)


class TestSimpleCashFlow:
    """SimpleCashFlow のテスト"""
    
    def test_calculate_simple_cf_positive(self):
        """プラスの簡易CF"""
        result = calculate_simple_cf(
            net_income=10_000_000,   # 1000万円利益
            depreciation=5_000_000,  # 500万円減価償却
            annual_repayment=8_000_000,  # 800万円返済
            year=2024
        )
        
        assert isinstance(result, SimpleCashFlow)
        # 簡易CF = 1000万 + 500万 - 800万 = 700万
        assert result.simple_cf == 7_000_000
        assert result.year == 2024
    
    def test_calculate_simple_cf_negative(self):
        """マイナスの簡易CF（返済能力不足）"""
        result = calculate_simple_cf(
            net_income=3_000_000,
            depreciation=2_000_000,
            annual_repayment=8_000_000,  # 返済が多すぎる
            year=2024
        )
        
        # 簡易CF = 300万 + 200万 - 800万 = -300万
        assert result.simple_cf == -3_000_000
    
    def test_calculate_simple_cf_zero_repayment(self):
        """返済ゼロ（無借金経営）"""
        result = calculate_simple_cf(
            net_income=5_000_000,
            depreciation=3_000_000,
            annual_repayment=0,
            year=2024
        )
        
        # 簡易CF = 500万 + 300万 - 0 = 800万
        assert result.simple_cf == 8_000_000


class TestSimpleCashFlowFromData:
    """calculate_simple_cf_from_data のテスト"""
    
    def test_from_data_basic(self):
        """基本的なデータ構造から計算"""
        data = [
            {
                "year": 2022,
                "net_income": 8_000_000,
                "depreciation": 4_000_000,
                "annual_repayment": 6_000_000
            },
            {
                "year": 2023,
                "net_income": 10_000_000,
                "depreciation": 4_500_000,
                "annual_repayment": 6_000_000
            },
            {
                "year": 2024,
                "net_income": 12_000_000,
                "depreciation": 5_000_000,
                "annual_repayment": 6_000_000
            }
        ]
        
        result = calculate_simple_cf_from_data(data)
        
        assert isinstance(result, SimpleCashFlowOutput)
        assert len(result.years) == 3
        # 平均CF計算確認
        assert result.average_simple_cf is not None
    
    def test_from_data_single_year(self):
        """単年データ"""
        data = [
            {
                "year": 2024,
                "net_income": 5_000_000,
                "depreciation": 2_000_000,
                "annual_repayment": 3_000_000
            }
        ]
        
        result = calculate_simple_cf_from_data(data)
        
        assert len(result.years) == 1
        assert result.years[0].simple_cf == 4_000_000  # 500万 + 200万 - 300万


class TestCashFlowModels:
    """キャッシュフローモデルのテスト"""
    
    def test_cashflow_statement_model(self):
        """CashFlowStatementモデル"""
        stmt = CashFlowStatement(
            year=2024,
            net_income=10_000_000,
            depreciation=5_000_000,
            operating_cf=12_000_000,
            investing_cf=-8_000_000,
            financing_cf=-3_000_000,
            net_cf=1_000_000,
            beginning_cash=20_000_000,
            ending_cash=21_000_000
        )
        
        assert stmt.year == 2024
        assert stmt.operating_cf == 12_000_000
    
    def test_cashflow_metrics_model(self):
        """CashFlowMetricsモデル"""
        metrics = CashFlowMetrics(
            year=2024,
            cf_repayment_years=5.5,
            debt_service_coverage=1.2,
            current_ratio=1.5,
            quick_ratio=1.0,
            cash_months=3.0,
            liquidity_assessment="普通",
            repayment_assessment="要改善"
        )
        
        assert metrics.cf_repayment_years == 5.5
        assert metrics.debt_service_coverage == 1.2
    
    def test_simple_cashflow_model(self):
        """SimpleCashFlowモデル"""
        scf = SimpleCashFlow(
            year=2024,
            net_income=10_000_000,
            depreciation=5_000_000,
            annual_repayment=8_000_000,
            simple_cf=7_000_000,
            debt_coverage=1.875,
            monthly_surplus=583_333
        )
        
        assert scf.simple_cf == 7_000_000
        assert scf.debt_coverage == 1.875


class TestCashFlowEngine:
    """CashFlowEngine のテスト"""
    
    def test_engine_creation(self):
        """エンジンの作成"""
        engine = CashFlowEngine()
        
        assert engine is not None
    
    def test_engine_has_methods(self):
        """必要なメソッドが存在"""
        engine = CashFlowEngine()
        
        assert hasattr(engine, 'calculate_cf')
        assert hasattr(engine, '_calculate_single_year_cf')
        assert hasattr(engine, '_assess_liquidity')
        assert hasattr(engine, '_assess_repayment')
