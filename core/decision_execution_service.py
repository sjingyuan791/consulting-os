import datetime
from typing import Dict, Any, List

# Supabase
from core.supabase_client import get_supabase_client

# Schemas and Models
# Schemas and Models
from core.schemas.common import ModuleMeta
# We need to import the pipeline logic for Execution and Simulation
from core.execution_roadmap_generator import generate_execution_roadmap, ExecutionRoadmap
from core.financial_simulation import simulate_outcome, SimulationResultSchema
# We might need StrategyOptionSchema to manipulate the snapshot
from core.strategy_hypothesis import StrategyOption

import hashlib
import json
import datetime
import subprocess
import threading
import time
from typing import Dict, Any, Optional

# Supabase
from core.supabase_client import get_supabase_client

# Schemas and Models
from core.schemas.common import ModuleMeta
from core.execution_roadmap_generator import generate_execution_roadmap, ExecutionRoadmap
from core.financial_simulation import simulate_outcome, SimulationResultSchema
from core.strategy_hypothesis import StrategyOption


def validate_override_parameters(params: Dict[str, Any]):
    """
    Validates user-provided override parameters for safety and sanity.
    """
    allowed_keys = {"investment", "timeline"}
    
    unknown = set(params.keys()) - allowed_keys
    if unknown:
        raise ValueError(f"Invalid parameters: {unknown}")

    if "investment" in params:
        try:
            val = float(params["investment"])
            if val < 0:
                raise ValueError("Investment cannot be negative.")
        except (ValueError, TypeError):
             raise ValueError("Investment must be a valid number.")
             
    if "timeline" in params:
        try:
            val = float(params["timeline"])
            if val < 1 or val > 120:
                raise ValueError("Timeline must be between 1 and 120 months.")
        except (ValueError, TypeError):
             raise ValueError("Timeline must be a valid number.")

def get_git_revision_hash() -> str:
    """
    Retrieves the current git commit hash for lineage tracking.
    Disabled in production environment for security.
    """
    import os
    
    # Disable in production environment
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        return "production-build"
    
    try:
        # We assume the CWD is the repo root or inside it.
        # timeout=1 to prevent hanging if something is wrong.
        result = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], 
            stderr=subprocess.DEVNULL, 
            timeout=1
        ).decode('ascii').strip()
        return result[:12]  # Short hash for brevity
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return "no-git-revision"

def compute_module_hash():
    """
    Computes a hash of the current module versions/state.
    Combines git hash with a timestamp or other factors if needed.
    """
    git_hash = get_git_revision_hash()
    return f"{git_hash}"

class AsyncExecutionManager:
    """
    Manages background execution of strategy tasks.
    """
    
    @staticmethod
    def run_in_background(strategy_run_id, decision_id, snapshot, guardrails_schema, dataset_versions, decided_by, execution_run_id):
        """
        Entry point for the background thread.
        """
        def task():
            print(f"[AsyncWorker] Starting task for execution_run_id={execution_run_id}")
            try:
                sb = get_supabase_client()
                print("[AsyncWorker] Supabase client initialized.")
                
                # 1. Compute
                print("[AsyncWorker] Starting roadmap design...")
                roadmap: ExecutionRoadmap = generate_execution_roadmap(
                    strategy_option=snapshot,
                    overrides={} # Could pass overrides if available
                )
                roadmap.meta["dataset_versions"] = dataset_versions
                print("[AsyncWorker] Roadmap design completed.")
                
                # Financial Simulation
                print("[AsyncWorker] Fetching latest financials...")
                res_run = sb.table("strategy_runs").select("final_strategy_package_json").eq("id", strategy_run_id).single().execute()
                final_package = res_run.data.get("final_strategy_package_json", {})
                financial_health_data = final_package.get("financial_health", {})
                metrics_history = financial_health_data.get("metrics_history", [])
                latest_financials = metrics_history[-1] if metrics_history else None
                
                if latest_financials:
                    from core.financial_engine import FinancialHealthCheck
                    latest_fin_obj = FinancialHealthCheck(**latest_financials)
                    simulation = simulate_outcome(latest_fin_obj, roadmap, guardrails=guardrails_schema)
                else:
                    simulation = SimulationResultSchema(
                        base_case_revenue=0, projected_revenue=0, projected_cost=0, projected_profit=0, roi=0.0
                    )
                simulation.meta.dataset_versions = dataset_versions
                print("[AsyncWorker] Simulation completed.")
                
                # 2. Update DB with Results
                update_payload = {
                    "execution_roadmap_json": roadmap.model_dump(),
                    "financial_simulation_json": simulation.model_dump(),
                    "status": "COMPLETED",
                    "meta_json": {
                        "dataset_versions": dataset_versions,
                        "generated_at": datetime.datetime.now().isoformat(),
                        "confidence_score": 0.8 # Placeholder or calc
                    }
                }
                
                sb.table("strategy_execution_runs").update(update_payload).eq("id", execution_run_id).execute()
                print(f"[AsyncWorker] Async execution completed successfully for run {execution_run_id}")
                
            except Exception as e:
                print(f"[AsyncWorker] Async execution failed: {e}")
                import traceback
                traceback.print_exc()
                try:
                    sb = get_supabase_client() # Re-init just in case
                    sb.table("strategy_execution_runs").update({
                        "status": "FAILED",
                        "error_message": str(e)
                    }).eq("id", execution_run_id).execute()
                except Exception as inner_e:
                    print(f"[AsyncWorker] Failed to update status to FAILED: {inner_e}")

        # Start thread
        thread = threading.Thread(target=task)
        thread.start()


def run_execution_phase(strategy_run_id: str, decision_id: str):
    """
    Orchestrates the Strategy Execution Phase (Phase 7).
    Supports Multi-Option Strategy merging.
    """
    sb = get_supabase_client()
    
    # 1. Fetch Context (Strategy Run & Decision)
    run = sb.table("strategy_runs").select("*").eq("id", strategy_run_id).single().execute()
    decision = sb.table("strategy_decisions").select("*").eq("id", decision_id).single().execute()
    
    if not run.data or not decision.data:
        return {"error": "Run or Decision not found"}
        
    strategy_pkg = run.data.get("final_strategy_package_json", {})
    all_options = strategy_pkg.get("strategy_options", {}).get("options", [])
    
    # 2. Parse Decision (Multi-Option)
    selected_options_meta = decision.data.get("selected_options_json", [])
    # Backward compatibility: if list is empty, check old single ID
    if not selected_options_meta and decision.data.get("selected_option_id"):
        selected_options_meta = [{"option_id": decision.data.get("selected_option_id"), "weight": 1.0, "phase": 1}]
        
    # 3. Idempotency Check
    existing = sb.table("strategy_execution_runs").select("id").eq("strategy_decision_id", decision_id).execute()
    if existing.data:
        return {"id": existing.data[0]["id"], "status": "EXISTING"}
        
    # 4. Generate & Merge Roadmaps
    # Note: We need to import the design service here or assume it's available.
    # For this implementation, we will mock the generation logic if imports are missing, 
    # but ideally we import `design_execution_roadmap` from `core.execution_design` (if it exists)
    # or `core.revenue_engine` etc. 
    # Since I don't recall seeing `core/execution_design.py` created, I will implement a lightweight generator here.
    
    merged_actions = []
    merged_kpis = []
    lineage_ids = []
    
    for meta in selected_options_meta:
        opt_id = meta.get("option_id")
        weight = meta.get("weight", 1.0)
        phase_start = meta.get("phase", 1)
        
        # Find Option Data
        opt_data = next((o for o in all_options if o["id"] == opt_id), None)
        if not opt_data: continue
        
        # Track Lineage
        if opt_data.get("origin_chat_message_id"):
            lineage_ids.append(opt_data["origin_chat_message_id"])
            
        # --- Centralized Roadmap Generation ---
        roadmap_obj: ExecutionRoadmap = generate_execution_roadmap(opt_data, overrides={})
        
        # Map new ExecutionRoadmapItem to DB format (compatible with UI)
        # UI likely expects 'title', 'description', 'phase', 'status'
        for item in roadmap_obj.items:
            # Add to merged actions for DB/UI
            merged_actions.append({
                "title": item.action,
                "description": f"Owner: {item.owner_role} | Impact: {item.expected_kpi_impact}",
                "phase": 1 if "Immediate" in item.timeline_phase else (2 if "Short" in item.timeline_phase else 3),
                "status": "PLANNED",
                "meta": item.model_dump()
            })
            
            # Add to temporary roadmap for simulation (we need to accumulate items)
            # Since generate_execution_roadmap returns a full object, we should merge items into a master roadmap
            # for the purpose of valid simulation input
            pass

    # 5. Financial Simulation
    # Re-construct a comprehensive ExecutionRoadmap for simulation
    from core.execution_roadmap_generator import ExecutionRoadmapItem
    
    # Convert merged_actions back to items or just collect them during the loop
    # Better to just collect items during the loop. Let's fix the loop above a bit in a follow-up or just map here.
    # Actually, let's just make a new ExecutionRoadmap from merged_actions meta
    simulation_items = []
    for action in merged_actions:
        # meta contains the dict of ExecutionRoadmapItem
        if "meta" in action:
            simulation_items.append(ExecutionRoadmapItem(**action["meta"]))
            
    aggregated_roadmap = ExecutionRoadmap(items=simulation_items)
    
    # Fetch Financial Context
    strategy_pkg = run.data.get("final_strategy_package_json", {})
    financial_health_data = strategy_pkg.get("financial_health", {})
    metrics_history = financial_health_data.get("metrics_history", [])
    latest_financials = metrics_history[-1] if metrics_history else None
    
    if latest_financials:
        from core.financial_engine import FinancialHealthCheck
        latest_fin_obj = FinancialHealthCheck(**latest_financials)
        # guardrails not strictly available here unless passed or fetched from somewhere else
        # decision might have guardrails? run might?
        # For now, pass None or try to find them.
        simulation = simulate_outcome(latest_fin_obj, aggregated_roadmap)
        simulation_result = simulation.model_dump()
        simulation_result["status"] = "SIMULATED"
    else:
        simulation_result = {
            "status": "SKIPPED", 
            "aggregated_impact": "No financial history available for simulation."
        }
    
    # 6. Atomic Insert (Insert-Only)
    new_run = {
        "strategy_run_id": strategy_run_id,
        "strategy_decision_id": decision_id,
        "execution_roadmap_json": {"actions": merged_actions},
        "financial_simulation_json": simulation_result,
        "status": "COMPLETED",
        "dataset_version_set_json": run.data.get("dataset_version_set_json"),
        "module_version_hash": "v2.0-multi-opt", 
        "assumed_kpi_targets_json": decision.data.get("assumed_kpi_targets_json", {}),
        "decision_lineage_json": {"origin_chat_ids": lineage_ids}
    }
    
    res = sb.table("strategy_execution_runs").insert(new_run).execute()
    
    # 7. Close the Loop: Initialize Monitoring
    try:
        from core.execution_monitoring_engine import initialize_monitoring_run
        # We don't have user_id readily available in params? 
        # Actually run entry has created_by if we look up strategy_run, but for now we pass None or infer.
        # strategy_decisions table has decided_by
        initialize_monitoring_run(res.data[0]['id'], user_id=decision.data.get("decided_by"))
    except Exception as e:
        print(f"Warning: Failed to initialize monitoring: {e}")
    
    return res.data[0]



