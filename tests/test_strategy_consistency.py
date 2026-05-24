import unittest
import sys
import os
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.midterm_plan_engine import MidtermPlanEngine
from core.schemas.refinement_schema import (
    RefinedStrategicPlan, FinancialModelAssumptions, ExternalConstraints, 
    DecisionGradeStatus, SimulationYear, FinancialSimulation, 
    BusinessModel, RevenueLogic, KPINode, ExecutionRoadmap, 
    Provenance, ProvenanceType, MissingInput
)
from core.quality_gate_enhanced import check_strategic_refinement_quality

class TestStrategyConsistency(unittest.TestCase):
    
    def setUp(self):
        self.engine = MidtermPlanEngine()
        
        # Mock Provenance
        self.prov = Provenance(source_tag=ProvenanceType.ASSUMPTION, source_detail="Test", confidence=1.0)
        
        # Valid Mock Plan Components
        self.valid_assumptions = FinancialModelAssumptions(
            revenue_growth_rate_y1=0.1,
            revenue_growth_rate_y2=0.1,
            revenue_growth_rate_y3=0.1,
            gross_margin_rate=0.5,
            opex_growth_rate=0.05,
            investment_amount_y1=100,
            investment_amount_y2=100,
            investment_amount_y3=100,
            tax_rate=0.3,
            provenance=self.prov
        )
        
        self.valid_constraints = ExternalConstraints(
            market_growth_rate=0.05,
            demand_ceiling=None,
            competitive_density_index=0.5,
            price_pressure_level="Medium",
            cost_inflation_rate=0.02,
            regulatory_risk_level="Low"
        )
        
        self.valid_plan = RefinedStrategicPlan(
            business_model=BusinessModel(
                model_name="Test Model", description="Desc", 
                revenue_drivers=["Price", "Vol"], customer_segments=["Seg1"],
                value_proposition="Val", operating_constraints=[],
                provenance=self.prov
            ),
            revenue_logic=RevenueLogic(equation="P*Q", components=[], description="Logic", provenance=self.prov), # Simplified
            kpi_tree=KPINode(name="KGI", definition="Def", unit="JPY", measurement_frequency="M", provenance=self.prov),
            financial_assumptions=self.valid_assumptions,
            execution_roadmap=ExecutionRoadmap(initiatives=[]),
            missing_inputs=[],
            falsification_conditions=["Cond1"],
            confidence_level=0.9,
            consistency_findings=[],
            financials_verified=True,
            external_constraints=self.valid_constraints,
            forecast_source="deterministic_engine",
            simulation=FinancialSimulation(
                is_verified=True, year_data=[], years=[], assumptions_used=self.valid_assumptions
            ) 
        )
        # Fix missing simulation years
        self.valid_plan.simulation.years = [
             SimulationYear(year=2025, revenue=100, cogs=50, gross_profit=50, opex=20, ebitda=30, operating_profit=20, net_profit=14, cash_flow=10)
        ]

    def test_decision_grade_approval(self):
        """Test that a fully valid plan gets approved."""
        status = check_strategic_refinement_quality(self.valid_plan)
        self.assertEqual(status.status, "approved")
        self.assertEqual(len(status.blocking_reasons), 0)

    def test_decision_grade_blocked_unverified(self):
        """Test blocking if financials not verified."""
        self.valid_plan.financials_verified = False
        status = check_strategic_refinement_quality(self.valid_plan)
        self.assertEqual(status.status, "blocked")
        self.assertIn("財務データが未検証です (Financials Not Verified)", status.blocking_reasons)

    def test_decision_grade_blocked_wrong_source(self):
        """Test blocking if forecast source is assumption_only."""
        self.valid_plan.forecast_source = "assumption_only"
        status = check_strategic_refinement_quality(self.valid_plan)
        self.assertEqual(status.status, "blocked")
        self.assertTrue(any("財務予測ソースが不適切" in r for r in status.blocking_reasons))

    def test_decision_grade_blocked_missing_inputs(self):
        """Test blocking if missing inputs exist."""
        self.valid_plan.missing_inputs = [MissingInput(field_name="Details", reason="Unknown", impact="High")]
        status = check_strategic_refinement_quality(self.valid_plan)
        self.assertEqual(status.status, "blocked")
        self.assertTrue(any("必須入力項目が欠落" in r for r in status.blocking_reasons))
        
    def test_decision_grade_blocked_no_constraints(self):
        """Test blocking if external constraints are missing."""
        self.valid_plan.external_constraints = None
        status = check_strategic_refinement_quality(self.valid_plan)
        self.assertEqual(status.status, "blocked")
        self.assertIn("外部環境制約（External Constraints）が考慮されていません", status.blocking_reasons)

    def test_deterministic_simulation_logic(self):
        """Verify the arithmetic of the deterministic engine."""
        # Setup base data
        base_data = [{"year": 2024, "sales": 1000, "gross_profit": 500, "operating_profit": 100}]
        
        # Run simulation
        sim_result = self.engine._run_deterministic_simulation(
            self.valid_assumptions, 
            base_data,
            constraints=self.valid_constraints
        )
        
        # Verify Year 1
        # Growth 10% -> 1100
        y1 = sim_result.years[0]
        self.assertAlmostEqual(y1.revenue, 1100)
        
        # Verify COGS (Margin 50%) -> 550
        self.assertAlmostEqual(y1.gross_profit, 550)
        
        # Verify Year 2
        # Growth 10% -> 1210
        y2 = sim_result.years[1]
        self.assertAlmostEqual(y2.revenue, 1210)
        
    def test_simulation_respects_assumptions(self):
        """Ensure simulation strictly follows assumptions provided."""
        # Change assumptions
        self.valid_assumptions.revenue_growth_rate_y1 = 0.2 # 20%
        base_data = [{"year": 2024, "sales": 100, "gross_profit": 50, "operating_profit": 10}]
        
        sim_result = self.engine._run_deterministic_simulation(
            self.valid_assumptions, 
            base_data,
        )
        
        self.assertAlmostEqual(sim_result.years[0].revenue, 120)

if __name__ == '__main__':
    unittest.main()
