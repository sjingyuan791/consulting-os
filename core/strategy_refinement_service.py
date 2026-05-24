from typing import Dict, Any, Optional, List
import json
import uuid
from core.supabase_client import get_supabase_client
from core.schemas.strategy import StrategyResponse
from core.final_strategy_package import FinalStrategyPackageSchema

class StrategyRefinementService:
    """
    Manages the insert-only refinement loop for Strategy Evolution.
    """
    
    def __init__(self):
        self.sb = get_supabase_client()

    def commit_refinement(
        self,
        base_run_id: str,
        refined_options: List[Dict[str, Any]],
        reasoning_state: Dict[str, Any],
        refinement_reason: str,
        user_id: str,
        origin_chat_id: Optional[str] = None,
        monitoring_feedback: Optional[str] = None
    ) -> str:
        """
        Creates a NEW Strategy Run version based on the previous run + refinements.
        Returns the new run_id.
        """
        
        # 1. Fetch Base Run
        base_run = self.sb.table("strategy_runs").select("*").eq("id", base_run_id).single().execute()
        if not base_run.data:
            raise ValueError(f"Base Strategy Run {base_run_id} not found.")
            
        base_data = base_run.data
        base_package = base_data.get("final_strategy_package_json", {})
        
        # 2. Construct Refinement Context
        refinement_context = {
            "origin": "strategy_chat",
            "reason": refinement_reason,
            "origin_chat_message_id": origin_chat_id,
            "monitoring_feedback_used": monitoring_feedback is not None,
            "monitoring_feedback_snippet": monitoring_feedback[:200] if monitoring_feedback else None,
            "base_run_id": base_run_id
        }
        
        # 3. Apply Diffs to Package
        # We perform a deep copy conceptually by loading valid schema and updating
        new_package = base_package.copy()
        
        # A. Update Options
        if refined_options:
            # Validate against schema
            # We assume refined_options matches StrategyOptionItem format
            new_package["strategy_options"]["options"] = refined_options
            new_package["strategy_options"]["revised_by_refinement"] = True
            
        # B. Update Reasoning State (Issue Tree / Hypotheses) if provided
        if reasoning_state:
            # Map reasoning state back to package fields if applicable
            # The package has 'root_cause_diagnosis' -> 'issue_tree'
            if "issue_tree" in reasoning_state:
                new_package["root_cause_diagnosis"]["issue_tree"] = reasoning_state["issue_tree"]
                
        # C. Update Meta
        if "meta" not in new_package:
            new_package["meta"] = {}
        
        new_package["meta"]["refinement_version"] = new_package["meta"].get("refinement_version", 0) + 1
        new_package["meta"]["parent_run_id"] = base_run_id
        
        # 4. Commit via RPC (Atomic Insert)
        try:
            res = self.sb.rpc("rpc_commit_strategy_refinement", {
                "p_client_id": base_data["client_id"],
                "p_parent_run_id": base_run_id,
                "p_analysis_run_id": base_data["analysis_run_id"],
                "p_package": new_package,
                "p_refinement_context": refinement_context,
                "p_created_by": user_id
            }).execute()
            
            return res.data # The new UUID
            
        except Exception as e:
            raise RuntimeError(f"Failed to commit strategy refinement: {e}")

# Service Singleton
refinement_service = StrategyRefinementService()
