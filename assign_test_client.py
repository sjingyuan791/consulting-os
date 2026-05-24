import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Error: SUPABASE_SERVICE_KEY not found")
    exit(1)

try:
    supabase: Client = create_client(url, key)
    
    # 1. Get the first valid workspace
    print("Fetching valid workspace...")
    res = supabase.table("workspaces").select("id, name, owner_user_id").limit(1).execute()
    
    if not res.data:
        print("❌ No workspaces found. Please create one in the app first.")
        exit(1)
        
    target_workspace = res.data[0]
    target_ws_id = target_workspace['id']
    target_ws_name = target_workspace.get('name', 'N/A')
    
    print(f"Target Workspace: {target_ws_name} ({target_ws_id})")
    
    # 2. Find the Test Client
    print("Finding Test Client...")
    client_res = supabase.table("clients").select("id, name").eq("name", "Test Client - Seeding").execute()
    
    if not client_res.data:
        print("❌ Test Client not found.")
        exit(1)
        
    test_client = client_res.data[0]
    print(f"Found Test Client: {test_client['name']} ({test_client['id']})")
    
    # 3. Update the Client's Workspace ID
    print(f"Moving client to workspace '{target_ws_name}'...")
    update_res = supabase.table("clients").update({"workspace_id": target_ws_id}).eq("id", test_client['id']).execute()
    
    if update_res.data:
        print("✅ Success! Test Client is now in your workspace.")
    else:
        print("⚠️ Update returned no data (check if successful).")

except Exception as e:
    print(f"Error: {e}")
