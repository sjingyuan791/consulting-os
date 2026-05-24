import os
import sys
# Add current directory to path so we can import core modules
sys.path.append(os.getcwd())

from dotenv import load_dotenv
from core.dashboard_widgets import get_analysis_summary, get_strategic_kpis, get_execution_progress
from supabase import create_client

load_dotenv()

def verify_fix():
    print("--- Verifying Dashboard Fix (Phase 2) ---")
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    # Get a client ID
    clients = supabase.table("clients").select("id, name").limit(1).execute()
    if not clients.data:
        print("No clients found to test.")
        return
        
    client_id = clients.data[0]['id']
    client_name = clients.data[0]['name']
    print(f"Testing with Client: {client_name} ({client_id})")
    
    print("\n1. Testing get_analysis_summary()...")
    summary = get_analysis_summary(client_id)
    if summary:
        print("  [SUCCESS] Data retrieved:")
        print(f"    Score: {summary.get('score')}")
    else:
        print("  [FAILURE] No data returned from get_analysis_summary.")
        
    print("\n2. Testing get_strategic_kpis()...")
    kpis = get_strategic_kpis(client_id)
    if kpis:
        print(f"  [SUCCESS] Retrieved {len(kpis)} KPIs.")
        print(f"  First KPI: {kpis[0]}")
    else:
        print("  [FAILURE] No KPIs retrieved (check if Section 12 exists).")
    
    print("\n3. Testing get_execution_progress()...")
    progress = get_execution_progress(client_id)
    if progress:
        print("  [SUCCESS] Execution progress retrieved:")
        print(f"    Status: {progress.get('status_label')}")
        print(f"    Progress: {progress.get('progress')}%")
        print(f"    Total Actions: {progress.get('total')}")
    else:
        print("  [INFO] No execution progress found (even with fallback).")

if __name__ == "__main__":
    verify_fix()
