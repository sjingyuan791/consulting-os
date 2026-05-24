"""
Test E2E Pipeline Integration.
E2Eパイプライン統合テスト
"""
import pytest
import asyncio
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.pipeline.orchestrator import PipelineOrchestrator
from core.pipeline.stage1_roa_engine import ROAEngine
from core.schemas.pipeline_stages import (
    PipelineStatus, StageStatus, Stage1Output, ROABreakdown
)


def run_async(coro):
    """Helper to run async coroutine in sync test"""
    return asyncio.run(coro)


class TestE2EPipelineBasic:
    """E2E基本パイプラインテスト"""
    
    @pytest.fixture
    def complete_financial_data(self):
        """完全な財務データセット"""
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
            },
            "operational_data": {
                "employees": 50,
                "industry": "manufacturing",
                "size": "medium"
            },
            "market_data": {
                "industry_growth": 0.03,
                "market_share": 0.05
            }
        }
    
    def test_stage1_execution(self, complete_financial_data):
        """Stage 1 (ROA分析) の実行"""
        engine = ROAEngine(industry="manufacturing", size="medium")
        
        result = run_async(engine.compute(complete_financial_data))
        
        assert isinstance(result, Stage1Output)
        assert result.roa_breakdown is not None
        assert result.analysis_years == [2022, 2023, 2024]
        assert len(result.weak_financial_nodes) >= 0
        assert len(result.financial_hypotheses) >= 0
    
    def test_stage1_to_stage2_data_flow(self, complete_financial_data):
        """Stage 1 → Stage 2 のデータフロー確認"""
        engine = ROAEngine()
        
        result = run_async(engine.compute(complete_financial_data))
        
        # Stage 2の入力として必要な情報が含まれているか
        assert result.weak_financial_nodes is not None
        assert result.financial_hypotheses is not None
        assert result.suspected_problem_nodes is not None


class TestE2EDataConsistency:
    """E2Eデータ整合性テスト"""
    
    @pytest.fixture
    def minimal_financial_data(self):
        """最小限の財務データ"""
        return {
            "financial_statements": {
                "years": [2024],
                "revenue": {"2024": 50_000_000},
                "cost_of_goods_sold": {"2024": 30_000_000},
                "operating_expenses": {"2024": 15_000_000},
                "net_income": {"2024": 3_500_000},
                "total_assets": {"2024": 40_000_000},
                "total_equity": {"2024": 20_000_000},
                "current_assets": {"2024": 20_000_000},
                "current_liabilities": {"2024": 10_000_000},
                "inventory": {"2024": 8_000_000},
                "accounts_receivable": {"2024": 10_000_000},
                "fixed_assets": {"2024": 20_000_000},
            }
        }
    
    def test_roa_calculation_accuracy(self, minimal_financial_data):
        """ROA計算の正確性"""
        engine = ROAEngine()
        
        result = run_async(engine.compute(minimal_financial_data))
        
        # ROA = 純利益 / 総資産
        expected_roa = 3_500_000 / 40_000_000  # 0.0875
        assert result.roa_breakdown.roa == pytest.approx(expected_roa, rel=0.01)
    
    def test_roe_calculation_accuracy(self, minimal_financial_data):
        """ROE計算の正確性"""
        engine = ROAEngine()
        
        result = run_async(engine.compute(minimal_financial_data))
        
        # ROE = 純利益 / 自己資本
        expected_roe = 3_500_000 / 20_000_000  # 0.175
        assert result.roa_breakdown.roe == pytest.approx(expected_roe, rel=0.01)
    
    def test_profit_margin_calculation(self, minimal_financial_data):
        """利益率計算の正確性"""
        engine = ROAEngine()
        
        result = run_async(engine.compute(minimal_financial_data))
        
        # Profit Margin = 純利益 / 売上
        expected_margin = 3_500_000 / 50_000_000  # 0.07
        assert result.roa_breakdown.profit_margin == pytest.approx(expected_margin, rel=0.01)


class TestE2EEdgeCases:
    """E2Eエッジケーステスト"""
    
    def test_zero_profit_company(self):
        """利益ゼロの会社"""
        data = {
            "financial_statements": {
                "years": [2024],
                "revenue": {"2024": 50_000_000},
                "cost_of_goods_sold": {"2024": 35_000_000},
                "operating_expenses": {"2024": 15_000_000},
                "net_income": {"2024": 0},  # 利益ゼロ
                "total_assets": {"2024": 40_000_000},
                "total_equity": {"2024": 20_000_000},
                "current_assets": {"2024": 20_000_000},
                "current_liabilities": {"2024": 10_000_000},
                "inventory": {"2024": 8_000_000},
                "accounts_receivable": {"2024": 10_000_000},
                "fixed_assets": {"2024": 20_000_000},
            }
        }
        
        engine = ROAEngine()
        result = run_async(engine.compute(data))
        
        assert result.roa_breakdown.roa == 0
        assert result.roa_breakdown.roe == 0
    
    def test_loss_making_company(self):
        """赤字の会社"""
        data = {
            "financial_statements": {
                "years": [2024],
                "revenue": {"2024": 50_000_000},
                "cost_of_goods_sold": {"2024": 40_000_000},
                "operating_expenses": {"2024": 20_000_000},
                "net_income": {"2024": -10_000_000},  # 赤字
                "total_assets": {"2024": 40_000_000},
                "total_equity": {"2024": 20_000_000},
                "current_assets": {"2024": 20_000_000},
                "current_liabilities": {"2024": 10_000_000},
                "inventory": {"2024": 8_000_000},
                "accounts_receivable": {"2024": 10_000_000},
                "fixed_assets": {"2024": 20_000_000},
            }
        }
        
        engine = ROAEngine()
        result = run_async(engine.compute(data))
        
        # 赤字でも計算できる
        assert result.roa_breakdown.roa < 0
        assert result.roa_breakdown.roe < 0
    
    def test_high_leverage_company(self):
        """高レバレッジの会社"""
        data = {
            "financial_statements": {
                "years": [2024],
                "revenue": {"2024": 100_000_000},
                "cost_of_goods_sold": {"2024": 60_000_000},
                "operating_expenses": {"2024": 30_000_000},
                "net_income": {"2024": 7_000_000},
                "total_assets": {"2024": 100_000_000},
                "total_equity": {"2024": 10_000_000},  # 自己資本が少ない
                "current_assets": {"2024": 50_000_000},
                "current_liabilities": {"2024": 45_000_000},
                "inventory": {"2024": 20_000_000},
                "accounts_receivable": {"2024": 25_000_000},
                "fixed_assets": {"2024": 50_000_000},
            }
        }
        
        engine = ROAEngine()
        result = run_async(engine.compute(data))
        
        # 高レバレッジ = 資産/自己資本が高い
        leverage = result.roa_breakdown.financial_leverage
        assert leverage == pytest.approx(10.0, rel=0.01)  # 100M / 10M = 10


class TestE2EMultiYearAnalysis:
    """E2E複数年分析テスト"""
    
    def test_three_year_trend_analysis(self):
        """3年トレンド分析"""
        data = {
            "financial_statements": {
                "years": [2022, 2023, 2024],
                "revenue": {"2022": 80_000_000, "2023": 90_000_000, "2024": 100_000_000},  # 成長
                "cost_of_goods_sold": {"2022": 50_000_000, "2023": 54_000_000, "2024": 60_000_000},
                "operating_expenses": {"2022": 25_000_000, "2023": 27_000_000, "2024": 30_000_000},
                "net_income": {"2022": 3_500_000, "2023": 6_300_000, "2024": 7_000_000},  # 増益
                "total_assets": {"2022": 70_000_000, "2023": 80_000_000, "2024": 90_000_000},
                "total_equity": {"2022": 30_000_000, "2023": 35_000_000, "2024": 40_000_000},
                "current_assets": {"2022": 35_000_000, "2023": 40_000_000, "2024": 45_000_000},
                "current_liabilities": {"2022": 20_000_000, "2023": 22_000_000, "2024": 25_000_000},
                "inventory": {"2022": 10_000_000, "2023": 12_000_000, "2024": 15_000_000},
                "accounts_receivable": {"2022": 15_000_000, "2023": 18_000_000, "2024": 20_000_000},
                "fixed_assets": {"2022": 35_000_000, "2023": 40_000_000, "2024": 45_000_000},
            }
        }
        
        engine = ROAEngine()
        result = run_async(engine.compute(data))
        
        assert result.analysis_years == [2022, 2023, 2024]
        # 最新年のデータで分析
        assert result.roa_breakdown.roa > 0
    
    def test_declining_company_analysis(self):
        """業績悪化企業の分析"""
        data = {
            "financial_statements": {
                "years": [2022, 2023, 2024],
                "revenue": {"2022": 100_000_000, "2023": 90_000_000, "2024": 80_000_000},  # 減収
                "cost_of_goods_sold": {"2022": 60_000_000, "2023": 58_000_000, "2024": 56_000_000},
                "operating_expenses": {"2022": 30_000_000, "2023": 30_000_000, "2024": 30_000_000},
                "net_income": {"2022": 7_000_000, "2023": 1_400_000, "2024": -4_200_000},  # 減益→赤字
                "total_assets": {"2022": 90_000_000, "2023": 85_000_000, "2024": 80_000_000},
                "total_equity": {"2022": 45_000_000, "2023": 43_000_000, "2024": 38_000_000},
                "current_assets": {"2022": 45_000_000, "2023": 42_000_000, "2024": 40_000_000},
                "current_liabilities": {"2022": 22_000_000, "2023": 22_000_000, "2024": 22_000_000},
                "inventory": {"2022": 15_000_000, "2023": 14_000_000, "2024": 13_000_000},
                "accounts_receivable": {"2022": 20_000_000, "2023": 18_000_000, "2024": 17_000_000},
                "fixed_assets": {"2022": 45_000_000, "2023": 43_000_000, "2024": 40_000_000},
            }
        }
        
        engine = ROAEngine()
        result = run_async(engine.compute(data))
        
        # 赤字企業は弱点ノードが検出されるはず
        assert result.roa_breakdown.roa < 0
        # 仮説が生成される
        assert isinstance(result.financial_hypotheses, list)
