from typing import Optional, Dict, Any
from core.supabase_client import get_supabase_client
from core.schemas.strategy import GuardrailsSchema

def save_guardrails(client_id: str, payload: GuardrailsSchema) -> str:
    """
    Saves or updates strategic guardrails for a client.
    Returns the ID of the record.
    """
    sb = get_supabase_client()
    
    # Check if exists
    existing = sb.table("strategic_guardrails").select("id").eq("client_id", client_id).execute()
    
    data = {
        "client_id": client_id,
        "mission_objective": payload.mission_objective,
        "time_horizon_years": payload.time_horizon_years,
        "investment_limit": payload.investment_limit,
        "risk_tolerance": payload.risk_tolerance,
        "strategic_boundaries_json": payload.strategic_boundaries,
        "success_state_definition": payload.success_state_definition,
        "decision_rules_json": payload.decision_rules
    }
    
    if existing.data:
        # Update
        rec_id = existing.data[0]['id']
        sb.table("strategic_guardrails").update(data).eq("id", rec_id).execute()
        return rec_id
    else:
        # Insert
        res = sb.table("strategic_guardrails").insert(data).execute()
        return res.data[0]['id']

def get_latest_guardrails(client_id: str) -> Optional[GuardrailsSchema]:
    """
    Retrieves the latest guardrails for a client.
    """
    sb = get_supabase_client()
    res = sb.table("strategic_guardrails").select("*").eq("client_id", client_id).limit(1).execute()
    
    if not res.data:
        return None
        
    rec = res.data[0]
    return GuardrailsSchema(
        mission_objective=rec.get("mission_objective") or "",
        time_horizon_years=rec.get("time_horizon_years") or 3,
        investment_limit=float(rec.get("investment_limit") or 0),
        risk_tolerance=rec.get("risk_tolerance") or "Medium",
        strategic_boundaries=rec.get("strategic_boundaries_json") or {},
        success_state_definition=rec.get("success_state_definition") or "",
        decision_rules=rec.get("decision_rules_json") or {}
    )
