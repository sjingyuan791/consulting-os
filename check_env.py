import os
from dotenv import load_dotenv

load_dotenv()

keys = ["SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SERVICE_KEY", "SERVICE_ROLE_KEY"]
found = [k for k in keys if os.environ.get(k)]

print(f"Found service keys: {found}")
if "SUPABASE_KEY" in os.environ:
    print("SUPABASE_KEY is present.")
