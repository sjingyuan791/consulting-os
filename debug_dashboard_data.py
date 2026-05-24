import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    exit(1)

supabase: Client = create_client(url, key)

def list_tables():
    print("\n--- Listing All Tables in Public Schema ---")
    try:
        # Supabase doesn't allow direct access to information_schema via client easily without RPC, 
        # but we can try to infer or just try to select * from presumed tables.
        # Actually, let's try a raw SQL query if possible or just test existence of known variants.
        
        tables_to_check = [
            "clients", "workspaces", 
            "strategy_runs", "diagnosis_runs", "analysis_runs", 
            "midterm_plan_documents", "mid_term_plans",
            "strategy_execution_runs", "pipeline_runs", "stage_outputs"
        ]
        
        found_tables = []
        for t in tables_to_check:
            try:
                supabase.table(t).select("*").limit(1).execute()
                print(f"  [OK] Table '{t}' exists.")
                found_tables.append(t)
            except Exception as e:
                # print(f"  [MISSING] Table '{t}' error: {e}")
                pass
        
        print(f"Found tables: {found_tables}")
        return found_tables

    except Exception as e:
        print(f"Error listing tables: {e}")

def debug_dashboard_data():
    list_tables()
    print("\n--- Debugging Dashboard Data ---")
    
    # 1. List Clients
    print("\n1. Checking Clients Table:")
    clients = supabase.table("clients").select("*").execute()
    if not clients.data:
        print("No clients found.")
        return
    
    print(f"Found {len(clients.data)} clients.")
    for client in clients.data:
        client_id = client['id']
        client_name = client.get('name', 'Unknown')
        print(f"\nProcessing Client: {client_name} ({client_id})")
        
        # 2. Check Strategy Runs (Legacy strategy_runs)
        print("  - Checking Strategy Runs (Legacy strategy_runs)...")
        try:
            strategy_runs = supabase.table("strategy_runs").select("id, created_at, final_strategy_package_json").eq("client_id", client_id).order("created_at", desc=True).limit(1).execute()
            if strategy_runs.data:
                latest = strategy_runs.data[0]
                print(f"    Legacy runs found: {len(strategy_runs.data)}")
                print(f"    Latest ID: {latest.get('id')}")
                
                package = latest.get('final_strategy_package_json')
                if package:
                    print(f"    [FOUND] final_strategy_package_json. Keys: {list(package.keys())}")
                    fh = package.get("financial_health", {})
                    print(f"    Financial Health Score: {fh.get('overall_health_score')}")
                else:
                    print("    [MISSING] final_strategy_package_json is None.")
            else:
                print("    No legacy runs found.")
        except Exception as e:
            print(f"    Legacy check failed: {e}")

        # Check latest analysis_runs directly
        print("  - Checking Analysis Runs (Directly)...")
        try:
            diag_runs = supabase.table("analysis_runs").select("*").eq("client_id", client_id).order("created_at", desc=True).limit(1).execute()
            if diag_runs.data:
                latest_diag = diag_runs.data[0]
                print(f"    Latest Analysis Run ID: {latest_diag.get('id')}")
                print(f"    Keys: {list(latest_diag.keys())}")
        except Exception as e:
            print(f"    Analysis check failed: {e}")

        # 3. Check Midterm Plan Documents (KPIs)
        print("  - Checking Midterm Plan Documents (KPIs)...")
        plans = supabase.table("midterm_plan_documents") \
            .select("id, document_json") \
            .eq("client_id", client_id) \
            .execute()
            
        if plans.data:
            print(f"    Found {len(plans.data)} plans.")
            doc = plans.data[0].get('document_json', {})
            sections = doc.get("sections", [])
            print(f"    First section keys: {list(sections[0].keys()) if sections else 'No sections'}")
            
            # Check for Section 12 (KPIs)
            # Try matching by string "12" or int 12, or check all sections
            found_12 = False
            for s in sections:
                # print(f"    Section ID: {s.get('section_id')} or {s.get('id')}")
                sid = s.get("section_id") or s.get("id")
                if str(sid) == "12":
                    found_12 = True
                    print("    [FOUND] Section 12 found.")
                    data = s.get("data", {})
                    # Print entire data dict to see what's inside
                    print(f"    FULL DATA in Section 12: {data}")
                    kpis = data.get("strategic_kpis", [])
                    print(f"    KPIs in list: {len(kpis)}")
                    break
            
            if not found_12:
                print("    [MISSING] Section 12 NOT found in sections list.")
        else:
            print("    No midterm plans found.")

        # 4. Check Execution Progress
        print("  - Checking Execution Progress...")
        # Need a strategy run ID for this
        if strategy_runs.data:
            latest_run_id = strategy_runs.data[0]['id']
            exec_runs = supabase.table("strategy_execution_runs") \
                .select("id, execution_roadmap_json") \
                .eq("strategy_run_id", latest_run_id) \
                .execute()
                
            if exec_runs.data:
                print(f"    Found {len(exec_runs.data)} execution runs.")
                roadmap = exec_runs.data[0].get("execution_roadmap_json", {})
                actions = roadmap.get("actions", [])
                print(f"    Found {len(actions)} actions in roadmap.")
            else:
                print("    No execution runs found for the latest strategy run.")
        else:
            print("    Skipping execution check (no strategy run).")

if __name__ == "__main__":
    debug_dashboard_data()
