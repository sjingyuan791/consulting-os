import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Use SERVICE KEY to see all workspaces
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Error: SUPABASE_SERVICE_KEY not found")
    exit(1)

try:
    supabase: Client = create_client(url, key)
    
    # List Workspaces
    print("--- Workspaces ---")
    res = supabase.table("workspaces").select("*").execute()
    workspaces = res.data
    for w in workspaces:
        print(f"ID: {w.get('id')}, Name: {w.get('name', 'N/A')}, Owner: {w.get('owner_user_id')}")
    
    if not workspaces:
        print("⚠️ No workspaces found.")

    # Check the Test Client's current workspace
    print("\n--- Test Client ---")
    client_res = supabase.table("clients").select("id, name, workspace_id").eq("name", "Test Client - Seeding").execute()
    if client_res.data:
        print(f"Test Client Workspace ID: {client_res.data[0]['workspace_id']}")
    else:
        print("Test Client not found.")

except Exception as e:
    print(f"Error: {e}")
