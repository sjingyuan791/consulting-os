"""
Test Monthly Cash Flow Simulation.
月次CFシミュレーションのテスト
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.monthly_cashflow_simulation import (
    CashFlowDrivers, MonthlyCashFlowEngine, CashFlowForecast,
    simulate_monthly_cashflow
)


class TestCashFlowDrivers:
    """CashFlowDrivers モデルのテスト"""
    
    def test_default_config(self):
        """デフォルト設定の確認"""
        drivers = CashFlowDrivers(
            annual_sales=120_000_000,
        )
        
        assert drivers.annual_sales == 120_000_000
        assert drivers.collection_days == 30  # デフォルト
        assert drivers.payment_days == 30  # デフォルト
    
    def test_custom_payment_terms(self):
        """カスタム支払条件の設定"""
        drivers = CashFlowDrivers(
            annual_sales=120_000_000,
            collection_days=60,
            payment_days=45,
        )
        
        assert drivers.collection_days == 60
        assert drivers.payment_days == 45


class TestMonthlyCashFlowEngine:
    """MonthlyCashFlowEngine のテスト"""
    
    def test_basic_simulation(self):
        """基本的なCFシミュレーション"""
        drivers = CashFlowDrivers(
            annual_sales=120_000_000,
            cogs_ratio=0.60,
            collection_days=30,
            payment_days=30,
            monthly_fixed_costs=2_000_000,
            opening_cash=5_000_000,
        )
        
        engine = MonthlyCashFlowEngine(drivers)
        result = engine.simulate(start_year=2024, start_month=4, num_months=12)
        
        assert isinstance(result, CashFlowForecast)
        assert len(result.months) == 12
        
        # 各月のデータが存在する
        for month_data in result.months:
            assert hasattr(month_data, 'month')
            assert hasattr(month_data, 'closing_cash')
    
    def test_collection_delay(self):
        """回収サイトの遅延が反映されること"""
        drivers_short = CashFlowDrivers(
            annual_sales=120_000_000,
            cogs_ratio=0.50,
            collection_days=0,  # 即時回収
            payment_days=0,
            opening_cash=0,
        )
        
        drivers_long = CashFlowDrivers(
            annual_sales=120_000_000,
            cogs_ratio=0.50,
            collection_days=60,  # 2ヶ月後回収
            payment_days=0,
            opening_cash=0,
        )
        
        engine_short = MonthlyCashFlowEngine(drivers_short)
        engine_long = MonthlyCashFlowEngine(drivers_long)
        
        result_short = engine_short.simulate(start_year=2024, start_month=4, num_months=6)
        result_long = engine_long.simulate(start_year=2024, start_month=4, num_months=6)
        
        # 回収遅延がある場合、初月のキャッシュが少ない
        assert result_long.months[0].closing_cash <= result_short.months[0].closing_cash


class TestCashShortageWarning:
    """資金ショート警告のテスト"""
    
    def test_shortage_detected(self):
        """資金ショートが検出されること"""
        drivers = CashFlowDrivers(
            annual_sales=60_000_000,  # 月5百万
            cogs_ratio=0.80,
            collection_days=60,
            payment_days=0,
            monthly_fixed_costs=3_000_000,
            opening_cash=2_000_000,
        )
        
        engine = MonthlyCashFlowEngine(drivers)
        result = engine.simulate(start_year=2024, start_month=4, num_months=12)
        
        # どこかでマイナスになる
        negative_found = any(m.is_negative for m in result.months)
        assert negative_found or len(result.negative_months) > 0
    
    def test_no_shortage_healthy(self):
        """健全な場合はショートなし"""
        drivers = CashFlowDrivers(
            annual_sales=120_000_000,
            cogs_ratio=0.50,
            collection_days=30,
            payment_days=30,
            monthly_fixed_costs=1_000_000,
            opening_cash=20_000_000,
        )
        
        engine = MonthlyCashFlowEngine(drivers)
        result = engine.simulate(start_year=2024, start_month=4, num_months=12)
        
        # マイナス月がない or 少ない
        assert len(result.negative_months) == 0 or result.lowest_balance > 0


class TestSimulateMonthlyCashflow:
    """ファサード関数のテスト"""
    
    def test_facade_function(self):
        """ファサード関数の動作確認"""
        result = simulate_monthly_cashflow(
            annual_sales=100_000_000,
            collection_days=45,
            payment_days=30,
            cogs_ratio=0.60,
            monthly_fixed_costs=1_500_000,
            opening_cash=5_000_000,
            start_year=2024,
            start_month=4,
            num_months=12
        )
        
        assert result is not None
        assert len(result.months) == 12
        assert result.total_inflow > 0


class TestEdgeCases:
    """エッジケースのテスト"""
    
    def test_zero_sales(self):
        """売上ゼロの場合"""
        drivers = CashFlowDrivers(
            annual_sales=0,
            monthly_fixed_costs=1_000_000,
            opening_cash=10_000_000,
        )
        
        engine = MonthlyCashFlowEngine(drivers)
        result = engine.simulate(start_year=2024, start_month=4, num_months=6)
        
        # エラーなく実行できる
        assert result is not None
        # キャッシュが減少する
        assert result.months[-1].closing_cash < 10_000_000
    
    def test_short_simulation_period(self):
        """短期シミュレーション"""
        drivers = CashFlowDrivers(
            annual_sales=120_000_000,
        )
        
        engine = MonthlyCashFlowEngine(drivers)
        result = engine.simulate(start_year=2024, start_month=4, num_months=1)
        
        assert len(result.months) == 1
