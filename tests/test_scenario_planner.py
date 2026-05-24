"""
Test Scenario Planner.
シナリオプランナーのテスト
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.scenario_planner import (
    ScenarioPlanner, ScenarioCase, ScenarioAssumption, ScenarioAnalysis,
    ScenarioType, run_scenario_analysis
)


class TestScenarioPlanner:
    """ScenarioPlanner のテスト"""
    
    def test_planner_creation(self):
        """プランナーの作成"""
        planner = ScenarioPlanner()
        
        assert planner is not None
        assert hasattr(planner, 'SCENARIO_PARAMS')
    
    def test_planner_with_industry(self):
        """業種指定でのプランナー作成"""
        planner = ScenarioPlanner(industry="manufacturing")
        
        assert planner is not None
    
    def test_generate_scenarios(self):
        """3シナリオの生成"""
        planner = ScenarioPlanner(industry="manufacturing")
        
        result = planner.generate_scenarios(
            base_revenue=1000,  # 百万円
            base_cost=800,
            base_assets=500,
            base_year=2024,
            target_year=2027
        )
        
        assert isinstance(result, ScenarioAnalysis)
        assert result.best_case is not None
        assert result.base_case is not None
        assert result.worst_case is not None
    
    def test_scenario_probabilities(self):
        """シナリオ確率の合計が100%"""
        planner = ScenarioPlanner()
        
        result = planner.generate_scenarios(
            base_revenue=1000,
            base_cost=800,
            base_assets=500,
            base_year=2024,
            target_year=2027
        )
        
        total_prob = (
            result.best_case.probability +
            result.base_case.probability +
            result.worst_case.probability
        )
        
        assert total_prob == pytest.approx(1.0, rel=0.01)


class TestScenarioModels:
    """シナリオモデルのテスト"""
    
    def test_scenario_type_enum(self):
        """ScenarioType列挙型"""
        assert ScenarioType.BEST == "best"
        assert ScenarioType.BASE == "base"
        assert ScenarioType.WORST == "worst"
    
    def test_scenario_assumption_model(self):
        """ScenarioAssumption モデル"""
        assumption = ScenarioAssumption(
            variable="revenue_growth",
            base_value=0.05,
            scenario_value=0.10,
            rationale="市場拡大を想定",
            source="業界レポート"
        )
        
        assert assumption.variable == "revenue_growth"
        assert assumption.base_value == 0.05
        assert assumption.scenario_value == 0.10
    
    def test_scenario_case_model(self):
        """ScenarioCase モデル"""
        case = ScenarioCase(
            scenario_type=ScenarioType.BEST,
            name="楽観シナリオ",
            probability=0.25,
            description="市場環境が好転した場合",
            revenue_growth_rate=0.15,  # 必須フィールド
            projected_revenue=1200,
            projected_cost=900,
            projected_profit=300,
            assumptions=[]
        )
        
        assert case.scenario_type == ScenarioType.BEST
        assert case.projected_profit == 300


class TestScenarioAnalysisResults:
    """シナリオ分析結果のテスト"""
    
    def test_expected_value_calculation(self):
        """期待値の計算"""
        planner = ScenarioPlanner()
        
        result = planner.generate_scenarios(
            base_revenue=1000,
            base_cost=800,
            base_assets=500,
            base_year=2024,
            target_year=2027
        )
        
        # 期待値が計算されている
        assert result.expected_value_revenue > 0
        assert result.expected_value_profit != 0
    
    def test_strategic_implications(self):
        """戦略的含意の生成"""
        planner = ScenarioPlanner()
        
        result = planner.generate_scenarios(
            base_revenue=1000,
            base_cost=800,
            base_assets=500,
            base_year=2024,
            target_year=2027
        )
        
        # 戦略的含意が生成されている
        assert isinstance(result.strategic_implications, list)
    
    def test_get_all_cases(self):
        """全ケース取得"""
        planner = ScenarioPlanner()
        
        result = planner.generate_scenarios(
            base_revenue=1000,
            base_cost=800,
            base_assets=500,
            base_year=2024,
            target_year=2027
        )
        
        all_cases = result.get_all_cases()
        
        assert len(all_cases) == 3


class TestFacadeFunction:
    """ファサード関数のテスト"""
    
    def test_run_scenario_analysis(self):
        """run_scenario_analysis関数"""
        result = run_scenario_analysis(
            base_revenue=1000,
            base_cost=800,
            base_assets=500,
            industry="manufacturing",
            base_year=2024,
            target_year=2027
        )
        
        assert isinstance(result, ScenarioAnalysis)
        assert result.base_year == 2024
        assert result.target_year == 2027


class TestIndustryVariations:
    """業種別バリエーションのテスト"""
    
    def test_service_industry(self):
        """サービス業"""
        planner = ScenarioPlanner(industry="service")
        
        result = planner.generate_scenarios(
            base_revenue=500,
            base_cost=400,
            base_assets=200,
            base_year=2024,
            target_year=2027
        )
        
        assert result is not None
    
    def test_retail_industry(self):
        """小売業"""
        planner = ScenarioPlanner(industry="retail")
        
        result = planner.generate_scenarios(
            base_revenue=800,
            base_cost=700,
            base_assets=300,
            base_year=2024,
            target_year=2027
        )
        
        assert result is not None
