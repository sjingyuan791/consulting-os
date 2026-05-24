from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.schemas.common import StrategyModuleSchema

# Define the new structured roadmap item as requested
class ExecutionRoadmapItem(BaseModel):
    action: str = Field(..., description="Actionable step title")
    owner_role: str = Field(..., description="Role responsible for execution")
    required_capability: str = Field(..., description="Skill or resource needed")
    investment_required: float = Field(default=0.0, description="Estimated cost")
    expected_kpi_impact: str = Field(..., description="Projected impact on KPIs")
    dependencies: List[str] = Field(default_factory=list, description="Prerequisite actions")
    timeline_phase: str = Field(..., description="Phase: 'Immediate', 'Short-term', 'Medium-term'")

class ExecutionRoadmap(BaseModel):
    items: List[ExecutionRoadmapItem]
    meta: Dict[str, Any] = {}

def generate_execution_roadmap(strategy_option: Any, overrides: Optional[Dict[str, Any]] = None) -> ExecutionRoadmap:
    """
    Generates a structured execution roadmap based on the selected strategy option.
    Centralized logic replacing scattered heuristics.
    """
    overrides = overrides or {}
    
    # Extract Strategy Metadata
    strat_name = getattr(strategy_option, "name", "Unknown Strategy")
    description = getattr(strategy_option, "description", "")
    rationale = getattr(strategy_option, "rationale", "")
    
    items = []
    
    # 1. Foundation / Setup Phase (Immediate)
    items.append(ExecutionRoadmapItem(
        action=f"Launch Initiative: {strat_name}",
        owner_role="Project Sponsor (Executive)",
        required_capability="Leadership Alignment",
        investment_required=0,
        expected_kpi_impact="Strategic Alignment",
        dependencies=[],
        timeline_phase="Immediate"
    ))
    
    # 2. Heuristic Generation based on Strategy Content
    # (In a real system, this would use LLM. For now, we use deterministic logic compatible with the previous 'design_execution_roadmap')
    
    steps = rationale.split('.')
    for i, step in enumerate(steps):
        step = step.strip()
        if len(step) < 10: continue
        
        phase = "Short-term" if i < 2 else "Medium-term"
        owner = "Project Manager"
        capability = "Project Management"
        inv = 0.0
        
        if "cost" in description.lower() or "efficiency" in description.lower():
            owner = "Operations Lead"
            capability = "Process Optimization"
        elif "marketing" in description.lower() or "customer" in description.lower():
            owner = "CMO / Marketing Lead"
            capability = "Digital Marketing"
            inv = 10000.0 # Placeholder assumption
            
        items.append(ExecutionRoadmapItem(
            action=step,
            owner_role=owner,
            required_capability=capability,
            investment_required=inv,
            expected_kpi_impact="Primary KPI Improvement",
            dependencies=[items[-1].action] if items else [],
            timeline_phase=phase
        ))
        
    # 3. Apply Overrides
    # If user provided overrides (e.g. investment, timeline), we might adjust metadata or items
    # For now, we attach them to meta or adjust the first item's investment if global
    
    return ExecutionRoadmap(items=items, meta={"generated_by": "ExecutionRoadmapGenerator", "overrides": overrides})
