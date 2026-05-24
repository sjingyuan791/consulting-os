from typing import List, Optional, Any
from core.schemas.common import StrategyModuleSchema

# Import schemas from the newly created modules
from core.financial_engine import FinancialHealthCheck
from core.execution_roadmap_generator import ExecutionRoadmap
from core.schemas.strategy import GuardrailsSchema

class SimulationResultSchema(StrategyModuleSchema):
    base_case_revenue: float
    projected_revenue: float
    projected_cost: float
    projected_profit: float
    roi: float
    assumptions: List[str] = []

def simulate_outcome(
    current_state: FinancialHealthCheck,
    roadmap: ExecutionRoadmap,
    guardrails: Optional[GuardrailsSchema] = None
) -> SimulationResultSchema:
    """
    Simulate the financial impact of the execution roadmap.
    Uses ExecutionRoadmap from execution_roadmap_generator.py.
    """
    
    # 1. Base Case (Current State)
    base_revenue = current_state.revenue
    base_profit = current_state.operating_profit
    
    # 2. Estimate Impact from Initiatives (ExecutionRoadmapItems)
    impact_rev = 0.0
    impact_cost_reduction = 0.0
    investment_cost = 0.0
    
    assumptions = []

    for item in roadmap.items:
        # Investment Cost
        # Use the investment_required field directly
        cost_estimate = item.investment_required
        investment_cost += cost_estimate
        
        # Revenue Impact Analysis
        # Heuristic based on expected_kpi_impact and action title
        is_revenue_driver = False
        if "Revenue" in item.expected_kpi_impact or "Sales" in item.action or "売上" in item.expected_kpi_impact or "集客" in item.action:
            is_revenue_driver = True
            
        # Cost Impact Analysis    
        is_cost_driver = False
        if "Cost" in item.expected_kpi_impact or "Efficiency" in item.action or "削減" in item.expected_kpi_impact or "効率" in item.action:
            is_cost_driver = True
            
        # Calculate Impact
        if is_revenue_driver:
            # Assume conservative 2% uplift per major initiative if not specified
            # In a real system, we'd parse specific numbers from expected_kpi_impact
            uplift = base_revenue * 0.02
            impact_rev += uplift
            assumptions.append(f"施策 '{item.action}' により、売上が {uplift:,.0f} 増加すると仮定。")
            
        if is_cost_driver:
            # Assume 2% cost reduction (of total costs)
            current_total_cost = base_revenue - base_profit
            savings = current_total_cost * 0.02
            impact_cost_reduction += savings
            assumptions.append(f"施策 '{item.action}' により、コストが {savings:,.0f} 削減されると仮定。")
            
        if not is_revenue_driver and not is_cost_driver:
            # Operational improvement without direct financial impact?
            pass

    # 3. Projections
    projected_revenue = base_revenue + impact_rev
    
    current_cost = base_revenue - base_profit
    projected_cost_structure = current_cost - impact_cost_reduction
    
    projected_profit = projected_revenue - projected_cost_structure
    
    # 4. ROI Calculation
    # ROI = (Net Profit Impact) / Investment
    net_profit_impact = (projected_profit - base_profit)
    
    roi = 0.0
    if investment_cost > 0:
        roi = (net_profit_impact / investment_cost) * 100
        
    # Check Guardrails
    if guardrails and guardrails.investment_limit > 0:
        if investment_cost > guardrails.investment_limit:
            assumptions.append(f"⚠️ 投資額 ({investment_cost:,.0f}) が設定された予算上限 ({guardrails.investment_limit:,.0f}) を超過しています。")
    
        
    return SimulationResultSchema(
        base_case_revenue=base_revenue,
        projected_revenue=projected_revenue,
        projected_cost=projected_cost_structure + investment_cost, # Showing total cash out including investment
        projected_profit=projected_profit - investment_cost, # Net after investment
        roi=roi,
        assumptions=assumptions
    )

if __name__ == "__main__":
    # Mock usage
    from core.financial_engine import FinancialHealthCheck
    from core.execution_roadmap_generator import ExecutionRoadmap, ExecutionRoadmapItem
    
    mock_state = FinancialHealthCheck(
        year=2023, revenue=100000, gross_profit=40000, operating_profit=10000, net_income=5000,
        gross_margin=0.4, operating_margin=0.1, net_margin=0.05
    )
    
    mock_roadmap = ExecutionRoadmap(
        items=[
            ExecutionRoadmapItem(
                action="Grow Sales", 
                owner_role="Sales", 
                required_capability="Sales",
                investment_required=10000,
                expected_kpi_impact="Revenue +10%",
                timeline_phase="Short-term"
            ),
            ExecutionRoadmapItem(
                action="Cut Costs", 
                owner_role="Ops",
                required_capability="Ops", 
                investment_required=5000,
                expected_kpi_impact="Cost -5%",
                timeline_phase="Immediate"
            )
        ]
    )
    
    res = simulate_outcome(mock_state, mock_roadmap)
    print(res.model_dump_json(indent=2))
