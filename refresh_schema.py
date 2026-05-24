import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

try:
    supabase: Client = create_client(url, key)
    # Sending a specialized command to reload schema cache is not directly exposed via py library easily,
    # but accessing the root or making a specific request might trigger it or we can try to re-init.
    
    # Actually, PGRST204 usually means the column suggests it is not in the exposed schema or the cache is stale.
    # Let's try to just list the columns first to see what PostgREST sees.
    
    # We can use the .rpc() call if there is a function, or just inspect via metadata if possible.
    # But for now, let's try to "wake up" the connection.
    print("Attempting to List Clients to refresh connection...")
    response = supabase.table("clients").select("*").limit(1).execute()
    print(f"Response: {response}")

except Exception as e:
    print(f"Error: {e}")
