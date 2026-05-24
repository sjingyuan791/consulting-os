"""
Test Initiative Impact Model.
施策別インパクトモデルのテスト
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.initiative_impact_model import (
    InitiativeInput, InitiativeType, ConfidenceLevel,
    InitiativeImpactEngine, ImpactModelResult, ImpactCalculation
)


class TestInitiativeInput:
    """InitiativeInput モデルのテスト"""
    
    def test_sales_initiative_creation(self):
        """売上施策の作成"""
        init = InitiativeInput(
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
        
        assert init.initiative_type == InitiativeType.NEW_CUSTOMER
        assert init.confidence == ConfidenceLevel.MEDIUM
        assert init.target_customers == 50
        assert init.conversion_rate == 0.10
    
    def test_cost_initiative_creation(self):
        """コスト削減施策の作成"""
        init = InitiativeInput(
            id="init_002",
            name="仕入先見直し",
            description="既存仕入先との価格交渉",
            initiative_type=InitiativeType.COST_VARIABLE,
            confidence=ConfidenceLevel.HIGH,
            implementation_months=3,
            current_cost=30_000_000,
            reduction_rate=0.05,
        )
        
        assert init.initiative_type == InitiativeType.COST_VARIABLE
        assert init.confidence == ConfidenceLevel.HIGH
        assert init.current_cost == 30_000_000
        assert init.reduction_rate == 0.05
    
    def test_investment_initiative_creation(self):
        """投資施策の作成"""
        init = InitiativeInput(
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
        
        assert init.initiative_type == InitiativeType.INVESTMENT
        assert init.initial_investment == 10_000_000
        assert init.annual_benefit == 3_000_000


class TestInitiativeImpactEngine:
    """InitiativeImpactEngine のテスト"""
    
    def test_single_sales_initiative(self):
        """単一の売上施策のインパクト計算"""
        engine = InitiativeImpactEngine(
            base_revenue=100_000_000,
            base_operating_profit=10_000_000
        )
        
        init = InitiativeInput(
            id="s001",
            name="新規顧客開拓",
            description="展示会出展",
            initiative_type=InitiativeType.NEW_CUSTOMER,
            confidence=ConfidenceLevel.MEDIUM,
            target_customers=50,
            conversion_rate=0.10,
            unit_price=500_000,
            margin_rate=0.30,
        )
        
        result = engine.calculate_all([init])
        
        assert isinstance(result, ImpactModelResult)
        assert len(result.calculations) == 1
        assert result.calculations[0].operating_profit_impact > 0
    
    def test_single_cost_initiative(self):
        """単一のコスト削減施策のインパクト計算"""
        engine = InitiativeImpactEngine(
            base_revenue=100_000_000,
            base_operating_profit=10_000_000
        )
        
        init = InitiativeInput(
            id="c001",
            name="仕入先見直し",
            description="価格交渉",
            initiative_type=InitiativeType.COST_VARIABLE,
            confidence=ConfidenceLevel.HIGH,
            current_cost=30_000_000,
            reduction_rate=0.05,
        )
        
        result = engine.calculate_all([init])
        
        assert len(result.calculations) == 1
        # コスト削減 = 3000万 × 5% = 150万円
        calc = result.calculations[0]
        assert calc.operating_profit_impact > 0
    
    def test_multiple_initiatives(self):
        """複数施策のインパクト計算"""
        engine = InitiativeImpactEngine(
            base_revenue=100_000_000,
            base_operating_profit=10_000_000
        )
        
        initiatives = [
            InitiativeInput(
                id="s001",
                name="売上施策",
                description="",
                initiative_type=InitiativeType.NEW_CUSTOMER,
                confidence=ConfidenceLevel.MEDIUM,
                target_customers=50,
                conversion_rate=0.10,
                unit_price=500_000,
                margin_rate=0.30,
            ),
            InitiativeInput(
                id="c001",
                name="コスト施策",
                description="",
                initiative_type=InitiativeType.COST_VARIABLE,
                confidence=ConfidenceLevel.HIGH,
                current_cost=30_000_000,
                reduction_rate=0.05,
            ),
        ]
        
        result = engine.calculate_all(initiatives)
        
        assert len(result.calculations) == 2
        assert result.summary.total_operating_profit_impact > 0
    
    def test_confidence_weighting(self):
        """確度によるインパクト加重"""
        engine = InitiativeImpactEngine(
            base_revenue=100_000_000,
            base_operating_profit=10_000_000
        )
        
        high_conf = InitiativeInput(
            id="high",
            name="高確度",
            description="",
            initiative_type=InitiativeType.COST_FIXED,
            confidence=ConfidenceLevel.HIGH,
            current_cost=10_000_000,
            reduction_rate=0.10,
        )
        
        low_conf = InitiativeInput(
            id="low",
            name="低確度",
            description="",
            initiative_type=InitiativeType.COST_FIXED,
            confidence=ConfidenceLevel.LOW,
            current_cost=10_000_000,
            reduction_rate=0.10,
        )
        
        result = engine.calculate_all([high_conf, low_conf])
        
        # サマリーに確度別インパクトが含まれる
        assert result.summary.high_confidence_impact >= 0
        assert result.summary.low_confidence_impact >= 0


class TestImpactCalculationDetails:
    """計算詳細のテスト"""
    
    def test_calculation_steps_recorded(self):
        """計算ステップが記録されること"""
        engine = InitiativeImpactEngine(
            base_revenue=100_000_000,
            base_operating_profit=10_000_000
        )
        
        init = InitiativeInput(
            id="test",
            name="テスト施策",
            description="",
            initiative_type=InitiativeType.NEW_CUSTOMER,
            confidence=ConfidenceLevel.MEDIUM,
            target_customers=100,
            conversion_rate=0.05,
            unit_price=500_000,
            margin_rate=0.25,
        )
        
        result = engine.calculate_all([init])
        calc = result.calculations[0]
        
        # 計算ステップが存在する
        assert len(calc.calculation_steps) > 0


class TestEdgeCases:
    """エッジケースのテスト"""
    
    def test_empty_initiatives(self):
        """施策なしの場合"""
        engine = InitiativeImpactEngine(
            base_revenue=100_000_000,
            base_operating_profit=10_000_000
        )
        
        result = engine.calculate_all([])
        
        assert result.summary.total_operating_profit_impact == 0
        assert result.projected_revenue == 100_000_000
    
    def test_zero_base_values(self):
        """基準値がゼロの場合"""
        engine = InitiativeImpactEngine(
            base_revenue=0,
            base_operating_profit=0
        )
        
        init = InitiativeInput(
            id="test",
            name="テスト",
            description="",
            initiative_type=InitiativeType.COST_FIXED,
            confidence=ConfidenceLevel.HIGH,
            current_cost=5_000_000,
            reduction_rate=0.10,
        )
        
        # ゼロ除算エラーが発生しないこと
        result = engine.calculate_all([init])
        assert result is not None
