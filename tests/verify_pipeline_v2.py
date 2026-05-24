import sys
import os
import uuid
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.supabase_client import get_supabase_client
from core.decision_execution_service import run_execution_phase
from core.execution_monitoring_engine import trigger_monitoring_run

def verify_pipeline():
    print("🚀 Starting Pipeline Verification...")
    sb = get_supabase_client()
    
    # 1. Setup Mock User & Client
    # In a real test we might fetch an existing user/client or create one.
    # We'll try to fetch the first available user/client to attach to.
    
    # 1. Setup Mock User & Client
    user_id = None
    client_id = None

    try:
        # Try to find an existing strategy run to hijack user/client
        existing_run = sb.table("strategy_runs").select("created_by, client_id").limit(1).execute()
        if existing_run.data:
            user_id = existing_run.data[0]['created_by']
            client_id = existing_run.data[0]['client_id']
            print(f"✅ Found existing User/Client from runs: {user_id} / {client_id}")
    except Exception as e:
        print(f"⚠️ Could not fetch existing runs: {e}")

    if not user_id:
        # Fallback to profiles/clients if no runs
        try:
            user_res = sb.table("profiles").select("id").limit(1).execute()
            if user_res.data:
                user_id = user_res.data[0]['id']
        except Exception:
            print("⚠️ Profiles table not accessible.")
            
    if not user_id:
        user_id = str(uuid.uuid4())
        print(f"⚠️ Using DUMMY User ID: {user_id}")

    if not client_id:
        try:
            client_res = sb.table("clients").select("id").limit(1).execute()
            if client_res.data:
                client_id = client_res.data[0]['id']
        except Exception:
             print("⚠️ Clients table not accessible.")
             
    if not client_id:
        client_id = str(uuid.uuid4())
        print(f"⚠️ Using DUMMY Client ID: {client_id}")

    # 2. Simulate Strategy Run (Phase 1-4 Output)
    run_id = str(uuid.uuid4())
    print(f"TEST: Creating Strategy Run {run_id}...")
    
    dummy_options = [
        {
            "id": "opt_A",
            "name": "Aggressive Expansion",
            "description": "Expand into US market",
            "impact": "High",
            "risk": "High",
            "origin_chat_message_id": str(uuid.uuid4())
        },
        {
            "id": "opt_B",
            "name": "Cost Optimization",
            "description": "Cut operational costs",
            "impact": "Medium",
            "risk": "Low",
            "origin_chat_message_id": str(uuid.uuid4())
        }
    ]
    
    strategy_pkg = {
        "strategy_options": {"options": dummy_options},
        "root_cause_diagnosis": {"issue_tree": {}},
        "meta": {"dataset_versions": {"v": 1}}
    }
    
    # Insert Strategy Run
    try:
        sb.table("strategy_runs").insert({
            "id": run_id,
            "client_id": client_id,
            "final_strategy_package_json": strategy_pkg,
            "status": "COMPLETED",
            "created_by": user_id
        }).execute()
        print("✅ Strategy Run Inserted")
    except Exception as e:
        print(f"❌ Failed to insert Strategy Run: {e}")
        return

    # 3. Simulate Multi-Option Decision (Phase 6)
    print("TEST: Making Multi-Option Decision...")
    decision_payload = {
        "strategy_run_id": run_id,
        "selected_options_json": [
            {"option_id": "opt_A", "weight": 0.7, "phase": 1},
            {"option_id": "opt_B", "weight": 0.3, "phase": 2}
        ],
        "assumed_kpi_targets_json": {
            "2025": {"revenue": 100, "margin": 20}
        },
        "decision_rationale_json": {"text": "Balanced approach"},
        "decided_by": user_id
    }
    
    try:
        dec_res = sb.table("strategy_decisions").insert(decision_payload).execute()
        decision_id = dec_res.data[0]['id']
        print(f"✅ Decision Created: {decision_id}")
    except Exception as e:
        print(f"❌ Failed to insert Decision: {e}")
        return

    # 4. Trigger Execution Run (Phase 7)
    print("TEST: Running Execution Phase...")
    try:
        exec_run = run_execution_phase(run_id, decision_id)
        if hasattr(exec_run, "get") and exec_run.get("error"):
            print(f"❌ Execution Phase Error: {exec_run['error']}")
            return
        
        exec_id = exec_run['id']
        print(f"✅ Execution Run Generated: {exec_id}")
        
        # Verify Lineage
        lineage = exec_run.get("decision_lineage_json", {})
        if "origin_chat_ids" in lineage:
            print(f"   Lineage Checks: Found {len(lineage['origin_chat_ids'])} origin IDs.")
    except Exception as e:
        print(f"❌ Failed Execution Phase: {e}")
        # traceback
        import traceback
        traceback.print_exc()
        return

    # 5. Trigger Monitoring (Phase 8)
    print("TEST: Triggering Monitoring Run...")
    actuals = {
        "2025": {"revenue": 90, "margin": 15} # 10% miss on revenue, 25% miss on margin
    }
    
    try:
        monitor_res = trigger_monitoring_run(exec_id, actuals, user_id)
        print(f"✅ Monitoring Run Completed: {monitor_res['id']}")
        
        analysis = monitor_res.get("gap_analysis_json", {})
        print("   Gap Analysis Summary:")
        for alert in analysis.get("alerts", []):
            print(f"   - {alert}")
            
    except Exception as e:
        print(f"❌ Failed Monitoring Phase: {e}")
        return

    print("\n🎉 PIPELINE VERIFICATION SUCCESSFUL")

if __name__ == "__main__":
    verify_pipeline()
