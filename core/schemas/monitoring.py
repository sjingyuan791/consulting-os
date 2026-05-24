from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from core.schemas.common import StrategyModuleSchema

class MonitoringFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    off_track_kpis: List[str] = Field(default_factory=list, description="List of KPIs that are off track")
    severity: List[str] = Field(default_factory=list, description="Severity levels corresponding to off-track KPIs")
    recommended_focus: List[str] = Field(default_factory=list, description="Recommended areas to focus on")

class MonitoringRunSchema(StrategyModuleSchema):
    model_config = ConfigDict(extra="ignore")
    execution_run_id: str = Field(..., description="ID of the execution run being monitored")
    kpi_actuals_json: Dict[str, Any] = Field(..., description="Actual KPI values")
    gap_analysis_json: Dict[str, Any] = Field(..., description="Gap analysis results")
    severity: str = Field(default="MINOR", description="Overall severity: CRITICAL, WARNING, MINOR")
    priority: int = Field(default=3, description="Priority score (1-5, 1 is highest)")
    structured_feedback_json: Optional[MonitoringFeedback] = Field(default=None, description="Structured feedback for Strategy Chat")
