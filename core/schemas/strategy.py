from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any

from core.schemas.common import StrategyModuleSchema

# --- Phase 1: Guardrails ---
class GuardrailsSchema(StrategyModuleSchema):
    model_config = ConfigDict(extra="ignore")
    mission_objective: str = Field(description="Company Mission/Vision/Objective")
    time_horizon_years: int = Field(default=3, description="Planning period in years")
    investment_limit: float = Field(default=0.0, description="Max investment capacity")
    risk_tolerance: str = Field(default="medium", description="low/medium/high")
    strategic_boundaries: Dict[str, List[str]] = Field(default_factory=dict, description="Exclusions like {no_entry_markets: [], excluded_models: []}")
    success_state_definition: str = Field(default="", description="Definition of success")
    decision_rules: Dict[str, Any] = Field(default_factory=dict, description="Financial thresholds etc.")

# --- Phase 3: Diagnosis (Root Cause) ---
class IssueNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(description="The issue description or hypothesis")
    children: List['IssueNode'] = Field(default_factory=list, description="Sub-issues or evidence")

class DiagnosisAction(BaseModel):
    title: str = Field(description="Action title")
    description: str = Field(description="Detailed description")
    priority: str = Field(description="High/Medium/Low")

class BankerView(BaseModel):
    overall_assessment: str = Field(description="Positive/Neutral/Negative")
    credit_concern: str = Field(description="Main concern regarding creditworthiness")
    positive_factors: List[str] = Field(default_factory=list, description="Strengths from a lender's perspective")
    negative_factors: List[str] = Field(default_factory=list, description="Weaknesses/Risks")

class DiagnosisReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    causal_structure: IssueNode = Field(description="Why-Tree / KPI Tree")
    mece_issues: List[str] = Field(default_factory=list, description="Key issues identified (MECE)")
    hypothesis: List[str] = Field(default_factory=list, description="Provisional hypotheses")
    blind_spots: List[str] = Field(default_factory=list, description="Alternative hypotheses / Blind spots")
    falsification_conditions: List[str] = Field(default_factory=list, description="Conditions to disprove hypothesis")
    missing_inputs: List[str] = Field(default_factory=list, description="Data effectively missing for deeper analysis")
    actions: List[DiagnosisAction] = Field(default_factory=list, description="Action plan")
    bank_view: BankerView = Field(description="Banker's perspective section")

# --- Phase 4: Strategy Hypothesis ---
class DataRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    priority: str = Field(description="High / Medium / Low")
    missing_data: str = Field(description="Name/Type of missing data")
    why_needed: str = Field(description="Reason why this data is critical")
    how_to_obtain: str = Field(description="Where user might find this (e.g. Sales Dept, Accounting)")
    required_format: str = Field(description="Expected columns or file format")

class StrategyOptionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(description="Unique ID for the option")
    name: str = Field(description="Short title of the strategy")
    description: str = Field(description="Detailed explanation")
    rationale: str = Field(description="Why this solves the root cause")
    feasibility: str = Field(description="Low/Medium/High")
    impact: str = Field(description="Low/Medium/High")
    feasibility_score: int = Field(description="1-10 score")
    impact_score: int = Field(description="1-10 score")
    risk: str = Field(description="Key risks")
    time_horizon: str = Field(description="Short/Medium/Long-term")
    pros: List[str] = Field(default_factory=list, description="Advantages")
    cons: List[str] = Field(default_factory=list, description="Disadvantages")
    investment_required: Optional[str] = Field(default=None, description="Estimated cost/investment (e.g. '500万円')")
    estimated_impact: Optional[str] = Field(default=None, description="Quantified impact (e.g. 'Revenue +5%')")
    origin_chat_message_id: Optional[str] = Field(default=None, description="UUID of the chat message where this option was generated")
    
    # New Strategic Dimensions
    risk_level: str = Field(default="Medium", description="Low, Medium, High, Critical")
    capital_intensity: str = Field(default="Medium", description="Low (People), Medium, High (Capex)")
    time_to_effect: str = Field(default="Medium", description="Immediate, Short, Medium, Long")

class StrategyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chat_response: str = Field(description="Natural language conversational response to the user.")
    issue_definition: str = Field(description="The core issue being addressed")
    hypotheses: List[str] = Field(description="At least 3 valid hypotheses")
    analytical_framework: str = Field(description="Framework used, e.g., 3C, 4P, VRIO")
    required_data: List[str] = Field(description="Data needed to verify hypotheses")
    data_requests: List[DataRequest] = Field(default_factory=list)
    preliminary_insight: str = Field(description="Current best guess based on available context")
    next_action: str = Field(description="Recommended next step")
    assumptions: List[str] = Field(description="Key assumptions made")
    uncertainty: str = Field(description="Level of uncertainty and why")
    issue_tree: IssueNode = Field(description="Hierarchical issue tree structure")
    confidence: float = Field(default=0.5, description="Confidence score 0.0-1.0")
    
    # Refinement Loop
    revised_strategy_options: Optional[List[StrategyOptionItem]] = Field(default=None, description="Proposed revisions to strategy options")
    revision_reason: Optional[str] = Field(default=None, description="Reason for revision")

class StrategyContext(BaseModel):
    company_summary: str
    financial_summary: str
    sales_summary: str
    market_summary: str
    kpi_tree: Dict[str, Any] = Field(default_factory=dict)
    risks: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    additional_data_summary: str = Field(default="", description="Summary of additional data uploaded by user")

# --- Phase 5: SWOT / Cross-SWOT ---
class CrossRef(BaseModel):
    option_id: str = Field(description="ID of the referenced StrategyOptionItem")
    rationale: str = Field(description="Why this option fits this quadrant")

class SWOTSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]

class CrossSWOTSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    so_strategies: List[CrossRef] = Field(default_factory=list)
    wo_strategies: List[CrossRef] = Field(default_factory=list)
    st_strategies: List[CrossRef] = Field(default_factory=list)
    wt_strategies: List[CrossRef] = Field(default_factory=list)

# --- Phase 6: Strategy Generation (Moved from strategy_hypothesis.py) ---
class StrategyOption(BaseModel):
    name: str = Field(..., description="Short title of the strategy (e.g., 'Market Penetration')")
    description: str = Field(..., description="Detailed explanation of the strategy")
    rationale: str = Field(..., description="Why this solves the root cause")
    feasibility: str = Field(..., description="Low, Medium, High")
    impact: str = Field(..., description="Low, Medium, High")
    feasibility_score: int = Field(default=5, description="1-10 scale for deterministic sorting")
    impact_score: int = Field(default=5, description="1-10 scale for deterministic sorting")
    id: str = Field(..., description="Unique ID for the option")
    risk: str = Field(..., description="Key risks associated")
    time_horizon: str = Field(..., description="Short-term, Medium-term, Long-term")

class StrategyOptionsSchema(StrategyModuleSchema):
    selected_context_summary: str = Field(..., description="Summary of why these options were generated")
    options: List[StrategyOption] = []
    recommended_option_index: int = Field(default=0, description="Index of the AI-recommended option")
    so_what_recommendation: str = Field(
        default="",
        description=(
            "Single decisive So What statement. Names the recommended option, cites a specific metric, "
            "explains why over alternatives, and states the first concrete action."
        ),
    )
