from typing import Optional
from pydantic import BaseModel, Field
from core.schemas.common import ModuleMeta
from core.strategic_guardrails import GuardrailsSchema
from core.external_intelligence import MarketStructureSchema
from core.internal_capability import CapabilityMatrixSchema
from core.financial_engine import FinancialEngineOutput
from core.root_cause_engine import IssueTreeSchema
from core.strategy_hypothesis import StrategyOptionsSchema
from core.execution_roadmap_generator import ExecutionRoadmap
from core.financial_simulation import SimulationResultSchema
from core.decision_layer import SelectedStrategySchema

class FinalStrategyPackageSchema(BaseModel):
    meta: ModuleMeta = Field(default_factory=ModuleMeta)
    
    # 1. Inputs & Status
    guardrails: GuardrailsSchema
    financial_health: FinancialEngineOutput
    external_intelligence: MarketStructureSchema
    internal_capability: CapabilityMatrixSchema
    
    # 2. Diagnosis
    root_cause_diagnosis: IssueTreeSchema
    
    # 3. Decision
    strategy_options: StrategyOptionsSchema
    selected_strategy: Optional[SelectedStrategySchema] = None
    
    # 4. Action Plan
    # 4. Action Plan (Execution Phase - Optional in Strategy Pipeline)
    execution_roadmap: Optional[ExecutionRoadmap] = None
    financial_simulation: Optional[SimulationResultSchema] = None
