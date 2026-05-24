"""
Test Pipeline Stage 1: ROA Engine.
パイプラインステージ1 ROAエンジンのテスト
"""
import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.pipeline.stage1_roa_engine import ROAEngine, create_roa_engine
from core.schemas.pipeline_stages import Stage1Output, ROABreakdown


def run_async(coro):
    """Helper to run async coroutine in sync test"""
    return asyncio.run(coro)


class TestROAEngine:
    """ROAEngine のテスト"""
    
    @pytest.fixture
    def sample_input_data(self):
        """ROAエンジンが期待する形式のサンプルデータ"""
        return {
            "financial_statements": {
                "years": [2022, 2023, 2024],
                "revenue": {"2022": 100_000_000, "2023": 110_000_000, "2024": 120_000_000},
                "cost_of_goods_sold": {"2022": 60_000_000, "2023": 66_000_000, "2024": 72_000_000},
                "operating_expenses": {"2022": 30_000_000, "2023": 33_000_000, "2024": 36_000_000},
                "net_income": {"2022": 7_000_000, "2023": 7_700_000, "2024": 8_400_000},
                "total_assets": {"2022": 80_000_000, "2023": 85_000_000, "2024": 90_000_000},
                "total_equity": {"2022": 40_000_000, "2023": 45_000_000, "2024": 50_000_000},
                "current_assets": {"2022": 40_000_000, "2023": 42_000_000, "2024": 45_000_000},
                "current_liabilities": {"2022": 20_000_000, "2023": 20_000_000, "2024": 20_000_000},
                "inventory": {"2022": 15_000_000, "2023": 16_000_000, "2024": 17_000_000},
                "accounts_receivable": {"2022": 20_000_000, "2023": 22_000_000, "2024": 24_000_000},
                "fixed_assets": {"2022": 40_000_000, "2023": 43_000_000, "2024": 45_000_000},
            }
        }
    
    def test_engine_creation(self):
        """エンジンの作成"""
        engine = ROAEngine()
        
        assert engine.STAGE_NUMBER == 1
        assert engine.STAGE_NAME == "ROA Deductive Engine"
    
    def test_engine_with_industry(self):
        """業種指定でのエンジン作成"""
        engine = ROAEngine(industry="retail", size="small")
        
        assert engine is not None
    
    def test_compute_basic(self, sample_input_data):
        """基本的なROA計算"""
        engine = ROAEngine()
        
        result = run_async(engine.compute(sample_input_data))
        
        assert isinstance(result, Stage1Output)
        assert result.roa_breakdown is not None
        assert result.analysis_years == [2022, 2023, 2024]
    
    def test_roa_breakdown_values(self, sample_input_data):
        """ROAブレークダウンの値"""
        engine = ROAEngine()
        
        result = run_async(engine.compute(sample_input_data))
        breakdown = result.roa_breakdown
        
        # ROA = 純利益 / 総資産
        expected_roa = 8_400_000 / 90_000_000
        assert breakdown.roa == pytest.approx(expected_roa, rel=0.01)
        
        # profit_margin = 純利益 / 売上
        expected_profit_margin = 8_400_000 / 120_000_000
        assert breakdown.profit_margin == pytest.approx(expected_profit_margin, rel=0.01)
    
    def test_weak_nodes_detection(self, sample_input_data):
        """弱点ノードの検出"""
        engine = ROAEngine()
        
        result = run_async(engine.compute(sample_input_data))
        
        # 弱点ノードがリストとして返される
        assert isinstance(result.weak_financial_nodes, list)
    
    def test_hypotheses_generation(self, sample_input_data):
        """仮説の生成"""
        engine = ROAEngine()
        
        result = run_async(engine.compute(sample_input_data))
        
        # 仮説がリストとして返される
        assert isinstance(result.financial_hypotheses, list)
    
    def test_yoy_changes(self, sample_input_data):
        """前年比変化の計算"""
        engine = ROAEngine()
        
        result = run_async(engine.compute(sample_input_data))
        
        # 前年比変化が計算されている
        if result.year_over_year_changes:
            assert isinstance(result.year_over_year_changes, dict)
    
    def test_analysis_summary(self, sample_input_data):
        """分析サマリーの生成"""
        engine = ROAEngine()
        
        result = run_async(engine.compute(sample_input_data))
        
        # サマリーが生成されている
        assert result.analysis_summary is not None
        assert len(result.analysis_summary) > 0


class TestROAEngineEdgeCases:
    """エッジケースのテスト"""
    
    def test_single_year_data(self):
        """1年分のデータのみ"""
        data = {
            "financial_statements": {
                "years": [2024],
                "revenue": {"2024": 100_000_000},
                "cost_of_goods_sold": {"2024": 60_000_000},
                "operating_expenses": {"2024": 30_000_000},
                "net_income": {"2024": 7_000_000},
                "total_assets": {"2024": 80_000_000},
                "total_equity": {"2024": 40_000_000},
                "current_assets": {"2024": 40_000_000},
                "current_liabilities": {"2024": 20_000_000},
                "inventory": {"2024": 15_000_000},
                "accounts_receivable": {"2024": 20_000_000},
                "fixed_assets": {"2024": 40_000_000},
            }
        }
        
        engine = ROAEngine()
        result = run_async(engine.compute(data))
        
        # エラーなく処理される
        assert result is not None
        assert len(result.analysis_years) == 1
    
    def test_zero_revenue(self):
        """売上ゼロの処理"""
        data = {
            "financial_statements": {
                "years": [2024],
                "revenue": {"2024": 0},
                "cost_of_goods_sold": {"2024": 0},
                "operating_expenses": {"2024": 0},
                "net_income": {"2024": 0},
                "total_assets": {"2024": 100_000_000},
                "total_equity": {"2024": 50_000_000},
                "current_assets": {"2024": 50_000_000},
                "current_liabilities": {"2024": 25_000_000},
                "inventory": {"2024": 0},
                "accounts_receivable": {"2024": 0},
                "fixed_assets": {"2024": 50_000_000},
            }
        }
        
        engine = ROAEngine()
        result = run_async(engine.compute(data))
        
        # ゼロ除算エラーなく処理
        assert result is not None
        assert result.roa_breakdown.roa == 0


class TestCreateROAEngine:
    """ファクトリー関数のテスト"""
    
    def test_factory_function(self):
        """create_roa_engine関数のテスト"""
        engine = create_roa_engine()
        
        assert isinstance(engine, ROAEngine)
        assert engine.STAGE_NUMBER == 1
