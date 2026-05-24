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
    print("Connection Object Created.")
    
    # Check if we can reach the server and if tables exist
    # Attempt to select from 'clients' table
    try:
        response = supabase.table("clients").select("*").limit(1).execute()
        print("Successfully connected to Supabase!")
        print(f"Clients table check: {response}")
        
        # Check 'dataset_versions'
        response = supabase.table("dataset_versions").select("*").limit(1).execute()
        print(f"dataset_versions table check: {response}")
        
    except Exception as e:
        print(f"Connection successful but table check failed. Did you run the migration SQL?\nError: {e}")

except Exception as e:
    print(f"Failed to connect to Supabase: {e}")
