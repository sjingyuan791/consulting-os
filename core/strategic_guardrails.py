from typing import List, Optional
from core.schemas.strategy import GuardrailsSchema

def define_guardrails(
    must_haves: List[str] = [],
    must_not_haves: List[str] = [],
    timeline_months: int = 12,
    budget_limit: Optional[float] = None,
    risk_tolerance: str = "Medium",
    existing_guardrails: Optional[GuardrailsSchema] = None
) -> GuardrailsSchema:
    """
    Constructs the Strategic Guardrails object.
    If existing_guardrails is provided, it returns that (or updates it).
    For backward compatibility, we map args to the new schema if needed, 
    but ideally we should just pass the stored schema.
    """
    if existing_guardrails:
        return existing_guardrails

    # Fallback to creating a new one (e.g. from pipeline args if no DB record)
    # Fallback to creating a new one (e.g. from pipeline args if no DB record)
    import uuid
    version_id = str(uuid.uuid4())
    snapshot = {
        "must_haves": must_haves,
        "must_not_haves": must_not_haves,
        "timeline_months": timeline_months,
        "budget_limit": budget_limit,
        "risk_tolerance": risk_tolerance
    }
    
    g_schema = GuardrailsSchema(
        mission_objective="Defined by Constraints",
        time_horizon_years=int(timeline_months/12),
        investment_limit=budget_limit if budget_limit else 0.0,
        risk_tolerance=risk_tolerance,
        strategic_boundaries={
            "must_haves": must_haves,
            "must_not_haves": must_not_haves
        }
    )
    g_schema.meta.guardrails_version_id = version_id
    g_schema.meta.assumptions_snapshot = snapshot
    return g_schema

if __name__ == "__main__":
    pass
