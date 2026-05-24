from pydantic import BaseModel, Field
from typing import List, Optional
from core.schemas.common import StrategyModuleSchema, ModuleMeta, EvidenceRef
from core.strategy_hypothesis import StrategyOptionsSchema
from core.strategic_guardrails import GuardrailsSchema

class SelectedStrategySchema(StrategyModuleSchema):
    chosen_option_id: str
    reasons: List[str] = []
    non_choices: List[str] = Field(default_factory=list, description="IDs of rejected options")
    exit_criteria: List[str] = Field(default_factory=list, description="Conditions to abandon this strategy")

def select_strategy(
    options: StrategyOptionsSchema,
    guardrails: GuardrailsSchema,
    risk_tolerance: str = "Medium", # Low, Medium, High
    dataset_versions: dict = {}
) -> SelectedStrategySchema:
    """
    Deterministic decision making based on explicit criteria.
    """
    meta = ModuleMeta(dataset_versions=dataset_versions)
    
    if not options.options:
        meta.missing_inputs.append({"missing_field": "options", "reason": "No options generated", "how_to_get": "Check Hypothesis Engine", "priority": "High"})
        return SelectedStrategySchema(chosen_option_id="NONE", meta=meta)
    
    # Simple Scoring Logic
    # Weighted Score: Feasibility (40%) + Impact (60%)
    # If Risk Tolerance Low -> Feasibility weight increases
    
    w_feas = 0.4
    w_imp = 0.6
    if risk_tolerance == "Low":
        w_feas = 0.7
        w_imp = 0.3
    
    scored_options = []
    for opt in options.options:
        score = (opt.feasibility_score * w_feas) + (opt.impact_score * w_imp)
        scored_options.append((score, opt))
        
    scored_options.sort(key=lambda x: x[0], reverse=True)
    
    best_score, best_opt = scored_options[0]
    
    # Construct Result
    chosen_id = best_opt.id
    non_choices = [opt.id for _, opt in scored_options if opt.id != chosen_id]
    
    reasons = [
        f"リスク許容度 '{risk_tolerance}' に基づく最高加重スコア ({best_score:.1f}) を獲得。",
        f"実現可能性: {best_opt.feasibility_score}/10, インパクト: {best_opt.impact_score}/10"
    ]
    
    meta.rules_fired.append(f"RiskBasedSelection(risk={risk_tolerance})")
    meta.evidence.append(EvidenceRef(source_type="module_output", dataset_id="strategy_hypothesis", pointer=f"option_id={chosen_id}", confidence=1.0))
    
    return SelectedStrategySchema(
        chosen_option_id=chosen_id,
        reasons=reasons,
        non_choices=non_choices,
        exit_criteria=["ROIが10%を下回った場合", "3ヶ月以内に競合が類似サービスを開始した場合"],
        meta=meta
    )
