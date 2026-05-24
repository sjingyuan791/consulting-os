from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from core.schemas.strategy import DataRequest

# --- Phase 6: Strategy Decision ---
class StrategyDecisionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Multi-option support
    selected_options_json: List[Dict[str, Any]] = Field(description="List of {option_id, weight, phase}")
    assumed_kpi_targets_json: Dict[str, Dict[str, float]] = Field(description="{year: {kpi_id: target}}")
    rejection_reasons: Dict[str, str] = Field(description="Map of rejected option_id -> reason")
    strategic_exclusions: str = Field(default="", description="Strategic trade-offs / What NOT to do")
    decision_rationale: str
    decision_rationale_json: Dict[str, Any] = Field(default_factory=dict)
    
    # Backward compatibility (optional)
    selected_option_id: Optional[str] = None
    approved_by: Optional[str] = None
    approval_date: Optional[str] = None

# --- Phase 7 & 8: Execution & Monitoring ---
class MonitoringRunSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    execution_run_id: str
    kpi_actuals_json: Dict[str, Dict[str, float]]
    gap_analysis_json: Dict[str, Any]
    created_at: str

class ActionItem(BaseModel):
    id: str
    title: str
    objective: str
    hypothesis: Optional[str] = None
    kpi_refs: List[str] = Field(default_factory=list, description="List of KPI IDs")
    owner: str = "Unassigned"
    due_date: Optional[str] = None
    status: str = "Not Started" # Not Started, In Progress, Done, Delayed
    next_step: Optional[str] = None
    memo: Optional[str] = None
    
    # Priority & Matrix
    priority: str = "Medium" # High, Medium, Low
    impact: int = 3 # 1-5 (5=High)
    effort: int = 3 # 1-5 (5=High)
    tags: List[str] = Field(default_factory=list)

class KPIActual(BaseModel):
    year_month: str
    value: float
    comment: Optional[str] = None

class KPIItem(BaseModel):
    id: str
    name: str
    definition: str
    unit: str
    data_source: Optional[str] = None
    frequency: str = "Monthly"
    targets: Dict[str, float] = Field(default_factory=dict, description="Key: YYYY-MM, Value: Target")
    actuals: Dict[str, KPIActual] = Field(default_factory=dict, description="Key: YYYY-MM")

class MonthlyReview(BaseModel):
    year_month: str
    kpi_gaps: Dict[str, float] = Field(default_factory=dict, description="KPI ID -> Gap")
    alerts: List[str] = Field(default_factory=list, description="Critical alerts based on gaps")
    summary: str = Field(description="LLM generated summary of progress")
    updated_hypotheses: List[str] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)

class ExecutionState(BaseModel):
    client_id: str
    actions: List[ActionItem] = Field(default_factory=list)
    kpis: List[KPIItem] = Field(default_factory=list)
    reviews: List[MonthlyReview] = Field(default_factory=list)
    data_backlog: List[DataRequest] = Field(default_factory=list)

class ExecutionRoadmapSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phases: List[Dict[str, Any]] = Field(description="Checkpoints/Milestones")
    actions: List[ActionItem]
    kpis: List[KPIItem]

class SimulationResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    projected_pl: Dict[str, Any] = Field(description="Yearly projected P&L")
    cash_flow_forecast: Dict[str, Any]
    roi_analysis: Dict[str, float]

class GapAnalysisSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: str
    kpi_gaps: Dict[str, float]
    root_cause_of_gap: str
    corrective_actions: List[str]
