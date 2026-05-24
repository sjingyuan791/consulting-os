import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.execution_roadmap_generator import generate_execution_roadmap, ExecutionRoadmap
from core.financial_simulation import simulate_outcome, SimulationResultSchema
from core.financial_engine import FinancialHealthCheck
from core.strategy_hypothesis import StrategyOption

def test_financial_simulation_integration():
    """
    Test that the execution roadmap generator and financial simulation work together.
    """
    # 1. Mock Strategy Option
    mock_option = StrategyOption(
        id="opt_growth_1",
        name="Aggressive Sales Growth",
        description="Increase sales force and marketing spend.",
        rationale="Market is growing, capture share.",
        feasibility="High",
        impact="High",
        risk="Medium",
        time_horizon="Short-term"
    )

    # 2. Generate Roadmap
    roadmap = generate_execution_roadmap(mock_option)
    assert isinstance(roadmap, ExecutionRoadmap)
    assert len(roadmap.items) > 0
    
    # 3. Mock Financial State
    current_state = FinancialHealthCheck(
        year=2024,
        revenue=100000.0,
        gross_profit=40000.0,
        operating_profit=10000.0,
        net_income=6000.0,
        gross_margin=0.4,
        operating_margin=0.1,
        net_margin=0.06
    )

    # 4. Run Simulation
    simulation = simulate_outcome(current_state, roadmap)
    
    assert isinstance(simulation, SimulationResultSchema)
    # Check that some impact was calculated (assuming overrides or defaults work)
    # The heuristic in simulate_outcome looks for keywords like "Revenue", "Sales", "Cost"
    # generate_execution_roadmap creates items based on description.
    # "marketing" in description -> "CMO" -> "Digital Marketing"
    # simulate_outcome checks: "Sales" in action? "Revenue" in KPI?
    
    print(f"Base Revenue: {simulation.base_case_revenue}")
    print(f"Projected Revenue: {simulation.projected_revenue}")
    print(f"ROI: {simulation.roi}")
    print(f"Assumptions: {simulation.assumptions}")
    
    assert simulation.projected_revenue >= simulation.base_case_revenue
    assert simulation.projected_cost > 0

    # Test with Cost Strategy
    mock_cost_option = StrategyOption(
        id="opt_cost_1",
        name="Cost Cutting",
        description="Improve efficiency and reduce cost.",
        rationale="Margins are low.",
        feasibility="Medium",
        impact="Medium",
        risk="Low",
        time_horizon="Immediate"
    )
    roadmap_cost = generate_execution_roadmap(mock_cost_option)
    sim_cost = simulate_outcome(current_state, roadmap_cost)
    
    assert sim_cost.projected_cost < (current_state.revenue - current_state.operating_profit) + 20000 # Rough check
