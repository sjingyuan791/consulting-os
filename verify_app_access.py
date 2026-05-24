import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Use the ANON key (public)
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    exit(1)

try:
    supabase: Client = create_client(url, key)
    print("Attempting to access 'clients' table with ANON key...")
    
    # Attempt to fetch all clients
    response = supabase.table("clients").select("*").execute()
    
    count = len(response.data)
    print(f"Records found: {count}")
    
    if count == 0:
        print("✅ SUCCESS: Anon key cannot see any records (RLS is active).")
    else:
        print(f"❌ WARNING: Anon key found {count} records! RLS might be misconfigured or policies allow public access.")
        print(f"Data sample: {response.data[0]}")

except Exception as e:
    print(f"Error accessing Supabase: {e}")
