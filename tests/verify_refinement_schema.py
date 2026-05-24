
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.schemas.refinement_schema import (
    RefinedStrategicPlan,
    BusinessModel,
    RevenueLogic,
    KPITree,
    KPINode,
    FinancialModelAssumptions,
    ExecutionRoadmap,
    Initiative,
    Provenance
)

def test_schema_validity():
    print("Testing Refinement Schema Validity...")

    # 1. Create dummy components
    biz_model = BusinessModel(
        model_name="SaaS Subscription",
        description="Standard SaaS model",
        target_segments=["SME", "Enterprise"],
        value_proposition="Automated consulting",
        monetization_mechanics="Monthly subscription per user",
        scalable_factors=["User count", "Feature tier"],
        constraints=["Server capacity"],
        provenance=Provenance(source_type="internal", source_id="doc_1", confidence_score=0.9)
    )

    rev_logic = RevenueLogic(
        equation="Revenue = Users * ARPU",
        variables=["Users", "ARPU"],
        dependencies=[],
        description="Simple multiplication",
        provenance=Provenance(source_type="assumption", confidence_score=0.8)
    )

    kpi_tree = KPITree(
        name="ARR",
        definition="Annual Recurring Revenue",
        target_value_3y="100M",
        children=[
            KPINode(
                name="New MRR",
                definition="New Monthly Recurring Revenue",
                metric_type="monetary",
                target_value_3y="5M/mo",
                children=[]
            )
        ],
        provenance=Provenance(source_type="financial", source_id="fin_xls_v1")
    )

    assumptions = FinancialModelAssumptions(
        revenue_growth_rate_y1=0.2,
        revenue_growth_rate_y2=0.3,
        revenue_growth_rate_y3=0.3,
        gross_margin_rate=0.6,
        opex_growth_rate=0.15,
        investment_ratio=0.1
    )

    roadmap = ExecutionRoadmap(
        initiatives=[
            Initiative(
                name="Platform Launch",
                owner="CTO",
                timeline_start="2025-04-01",
                timeline_end="2025-09-30",
                dependencies=[],
                milestones=["Beta Release", "GA"],
                resource_requirements="5 Engineers",
                risk_factors=["Delay in API"]
            )
        ]
    )

    # 2. Assemble full plan
    plan = RefinedStrategicPlan(
        financials_verified=True,
        business_model=biz_model,
        revenue_logic=rev_logic,
        kpi_tree=kpi_tree,
        financial_assumptions=assumptions,
        execution_roadmap=roadmap,
        simulation=None, # Optional
        missing_inputs=[],
        falsification_conditions=["Churn > 5%"],
        confidence_level=0.85,
        consistency_findings=["Dependencies checked"]
    )

    # 3. Validate JSON serialization
    json_str = plan.model_dump_json()
    assert "SaaS Subscription" in json_str
    assert "Revenue = Users * ARPU" in json_str
    
    print("✅ Schema instantiation and serialization successful.")
    print(json_str[:200] + "...")

    # 4. Test Guardrails (Optional fields)
    plan_unverified = RefinedStrategicPlan(
        financials_verified=False, # Critical flag
        business_model=biz_model,
        revenue_logic=rev_logic,
        kpi_tree=kpi_tree,
        financial_assumptions=assumptions,
        execution_roadmap=roadmap,
        missing_inputs=["Financial Data"], # Should be present if verification fails
        falsification_conditions=[],
        confidence_level=0.5,
        consistency_findings=["Financials missing"]
    )
    
    assert plan_unverified.financials_verified is False
    print("✅ Unverified plan guardrail check successful.")

if __name__ == "__main__":
    try:
        test_schema_validity()
        print("\n🎉 ALL TESTS PASSED")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
