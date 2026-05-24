import time
import uuid
import json
import datetime
from core.supabase_client import get_supabase_client
from core.decision_execution_service import run_execution_phase

def setup_dummy_data(sb):
    print("Setting up dummy data...")
    
    # 1. Create a minimal Strategy Run
    strategy_run_id = str(uuid.uuid4())
    dummy_package = {
        "strategy_options": {
            "options": [
                {
                    "id": "opt_1", 
                    "name": "Option 1", 
                    "description": "Test Description",
                    "rationale": "Test Rationale",
                    "feasibility": "High",
                    "impact": "High",
                    "risk": "Low",
                    "time_horizon": "Short-term",
                    "investment_required": 10000, 
                    "time_to_impact_months": 6,
                    "feasibility_score": 5,
                    "impact_score": 5
                }
            ]
        },
        "guardrails": {
            "budget_cap": 50000,
            "min_roi": 1.5
        },
        "meta": {
            "dataset_versions": {"sales_data": "v1"}
        },
        "financial_health": {
            "metrics_history": [
                {
                    "year": 2023,
                    "revenue": 100000, 
                    "gross_profit": 60000,
                    "operating_profit": 30000,
                    "net_income": 20000,
                    "gross_margin": 0.6,
                    "operating_margin": 0.3,
                    "net_margin": 0.2
                }
            ]
        }
    }
    
    sb.table("strategy_runs").insert({
        "id": strategy_run_id,
        "final_strategy_package_json": dummy_package
    }).execute()
    
    # 2. Create a Decision
    decision_id = str(uuid.uuid4())
    sb.table("strategy_decisions").insert({
        "id": decision_id,
        "strategy_run_id": strategy_run_id,
        "selected_option_id": "opt_1",
        "modified_parameters_json": {"investment": 15000},
        "decided_by": None # Can be null for test
    }).execute()
    
    return strategy_run_id, decision_id

def verify_async_execution():
    sb = get_supabase_client()
    
    try:
        # Setup
        s_id, d_id = setup_dummy_data(sb)
        print(f"Created Strategy Run: {s_id}")
        print(f"Created Decision: {d_id}")
        
        # Trigger Execution
        print("Triggering run_execution_phase...")
        result = run_execution_phase(s_id, d_id)
        
        exec_id = result["id"]
        status = result["status"]
        print(f"Execution initialized. ID: {exec_id}, Initial Status: {status}")
        
        if status != "PENDING":
             print(f"WARNING: Expected PENDING, got {status}. It might have finished instantly or logic changed.")
        
        # Poll
        print("Polling for completion...")
        for i in range(30):
            res = sb.table("strategy_execution_runs").select("*").eq("id", exec_id).single().execute()
            current_status = res.data["status"]
            print(f"Time {i}s: Status = {current_status}")
            
            if current_status == "COMPLETED":
                print("SUCCESS: Execution completed!")
                print(f"Module Hash: {res.data.get('module_version_hash')}")
                if "execution_roadmap_json" in res.data and res.data["execution_roadmap_json"]:
                    print("Execution Roadmap JSON is populated.")
                else:
                    print("FAILED: Execution Roadmap JSON is empty.")
                    
                if "financial_simulation_json" in res.data and res.data["financial_simulation_json"]:
                     print("Financial Simulation JSON is populated.")
                else:
                     print("FAILED: Financial Simulation JSON is empty.")
                return
            
            if current_status == "FAILED":
                print(f"FAILED: Execution failed with message: {res.data.get('error_message')}")
                return
                
            time.sleep(1)
            
        print("TIMEOUT: Execution took too long.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_async_execution()
