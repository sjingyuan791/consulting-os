import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    exit(1)

try:
    supabase: Client = create_client(url, key)
    # Check 'workspaces'
    response = supabase.table("workspaces").select("*").limit(1).execute()
    print("Successfully connected and queried 'workspaces' table!")
    print(f"Workspaces data: {response}")
        
except Exception as e:
    print(f"Failed to query 'workspaces': {e}")
