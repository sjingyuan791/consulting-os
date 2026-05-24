from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class EvidenceRef(BaseModel):
    source_type: str = Field(..., description="financial_data, interview, market_report, etc.")
    dataset_id: Optional[str] = None
    pointer: str = Field(..., description="Specific location/row/key")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class MissingInput(BaseModel):
    missing_field: str
    reason: str
    how_to_get: str
    priority: str = "Medium" # High, Medium, Low

class ModuleMeta(BaseModel):
    dataset_versions: Dict[str, int] = Field(default_factory=dict, description="Versions of input datasets used")
    rules_fired: List[str] = Field(default_factory=list, description="IDs of rules that triggered")
    missing_inputs: List[MissingInput] = Field(default_factory=list)
    falsifiers: List[str] = Field(default_factory=list, description="Conditions that would invalidate this result")
    evidence: List[EvidenceRef] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    generated_at: str = Field(default_factory=str) # timestamp
    
    # Validation / Lineage
    guardrails_version_id: Optional[str] = Field(default=None, description="UUID of the guardrails version used")
    assumptions_snapshot: Optional[Dict[str, Any]] = Field(default=None, description="Snapshot of key assumptions/constraints")

class StrategyModuleSchema(BaseModel):
    meta: ModuleMeta = Field(default_factory=ModuleMeta)
