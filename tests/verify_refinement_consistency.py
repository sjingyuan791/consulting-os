
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import json
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.midterm_plan_engine import MidtermPlanEngine, MidtermPlanDocument, SECTION_DEFINITIONS, MidtermPlanSection
from core.schemas.refinement_schema import RefinedStrategicPlan, FinancialSimulation

class TestStrategicRefinement(unittest.TestCase):
    def setUp(self):
        # Setup valid dummy data for RefinedStrategicPlan
        self.valid_plan_data = {
            "financials_verified": True,
            "business_model": {
                "model_name": "Test Model",
                "description": "Test Desc",
                "revenue_drivers": ["Users", "Price"],
                "customer_segments": ["A"],
                "value_proposition": "Value",
                "operating_constraints": ["Constraint"],
                "provenance": {"source_tag": "internal_data", "source_detail": "doc1", "confidence": 0.9}
            },
            "revenue_logic": {
                "equation": "A * B",
                "components": [
                    {"name": "A", "description": "Desc A", "variable_name": "A", "provenance": {"source_tag": "assumption", "source_detail": "user", "confidence": 0.8}}
                ],
                "description": "Logic",
            },
            "kpi_tree": {
                "name": "KGI",
                "definition": "Def",
                "unit": "USD",
                "measurement_frequency": "Yearly",
                "target_value_3y": 100.0,
                "children": [],
                "provenance": {"source_tag": "financial_data", "source_detail": "xls", "confidence": 0.9}
            },
            "financial_assumptions": {
                "revenue_growth_rate_y1": 0.1,
                "revenue_growth_rate_y2": 0.1,
                "revenue_growth_rate_y3": 0.1,
                "gross_margin_rate": 0.5,
                "opex_growth_rate": 0.05,
                "investment_amount_y1": 100.0,
                "investment_amount_y2": 100.0,
                "investment_amount_y3": 100.0,
                "provenance": {"source_tag": "assumption", "source_detail": "AI", "confidence": 0.7}
            },
            "execution_roadmap": {
                "initiatives": []
            },
            "missing_inputs": [],
            "falsification_conditions": ["Condition 1"],
            "confidence_level": 0.9,
            "consistency_findings": ["Finding 1"]
        }

    @patch('core.midterm_plan_engine.openai_client')
    def test_run_strategic_refinement_verified(self, mock_openai):
        # 1. Mock LLM Response (Verified = True)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(self.valid_plan_data)
        mock_openai.chat.completions.create.return_value = mock_response

        # 2. Init Engine
        engine = MidtermPlanEngine(pipeline_data={"financial": {"data": "exists"}}, guardrails={})
        
        # 3. Create Dummy Document
        doc = MidtermPlanDocument(
            document_id="test_doc",
            client_id="test_client",
            sections=[MidtermPlanSection(section_id=d["id"], section_title=d["title"], narrative="Test Content") for d in SECTION_DEFINITIONS]
        )

        # 4. Run Async Method
        loop = asyncio.new_event_loop()
        refined_plan = loop.run_until_complete(engine.run_strategic_refinement(doc))
        loop.close()

        # 5. Assertions
        self.assertIsInstance(refined_plan, RefinedStrategicPlan)
        self.assertTrue(refined_plan.financials_verified)
        self.assertIsNotNone(refined_plan.simulation) # Should generate simulation
        self.assertIsInstance(refined_plan.simulation, FinancialSimulation)
        print("✅ Verified case passed: Simulation generated.")

    @patch('core.midterm_plan_engine.openai_client')
    def test_run_strategic_refinement_unverified(self, mock_openai):
        # 1. Mock LLM Response (Verified = False)
        unverified_data = self.valid_plan_data.copy()
        unverified_data["financials_verified"] = False
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(unverified_data)
        mock_openai.chat.completions.create.return_value = mock_response

        # 2. Init Engine
        engine = MidtermPlanEngine(pipeline_data={}, guardrails={})
        
        # 3. Dummy Document
        doc = MidtermPlanDocument(
            document_id="test_doc_2",
            client_id="test_client_2",
            sections=[MidtermPlanSection(section_id=d["id"], section_title=d["title"], narrative="Test Content") for d in SECTION_DEFINITIONS]
        )

        # 4. Run Async Method
        loop = asyncio.new_event_loop()
        refined_plan = loop.run_until_complete(engine.run_strategic_refinement(doc))
        loop.close()

        # 5. Assertions
        self.assertIsInstance(refined_plan, RefinedStrategicPlan)
        self.assertFalse(refined_plan.financials_verified)
        self.assertIsNone(refined_plan.simulation) # Should NOT generate simulation
        print("✅ Unverified case passed: Simulation suppressed.")

if __name__ == "__main__":
    unittest.main()
