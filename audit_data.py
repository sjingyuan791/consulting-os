import os
import uuid
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    exit(1)

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    print(f"Failed to initialize Supabase client: {e}")
    exit(1)

def get_all_ids(table, column="id"):
    try:
        # Fetching all IDs. Note: Supabase limits rows by default (usually 1000). 
        # For a thorough audit, we might need pagination, but for now we assume < 1000 records or increase limit.
        response = supabase.table(table).select(column).execute()
        return {str(item[column]) for item in response.data}
    except Exception as e:
        print(f"Error fetching IDs from {table}: {e}")
        return set()

def check_orphans(child_table, child_column, parent_ids):
    print(f"\nChecking {child_table}.{child_column} against parent IDs...")
    try:
        # Determine ID column name based on table
        if child_table == "client_analysis_runs":
            id_col = "run_id"
        elif child_table == "client_datasets":
            id_col = "dataset_id"
        else:
            id_col = "id"
        
        # We fetch ID and the foreign key column
        response = supabase.table(child_table).select(f"{id_col}, {child_column}").execute()
        orphans = []
        for item in response.data:
            val = item.get(child_column)
            # If val is None, it might be allowed (nullable), but if it's set, it must exist in parent_ids
            if val is not None:
                if str(val) not in parent_ids:
                    orphans.append(item[id_col])
        
        if orphans:
            print(f"❌ Found {len(orphans)} orphans in {child_table}: {orphans}")
        else:
            print(f"✅ No orphans found in {child_table}.")
    except Exception as e:
        print(f"Error checking {child_table}: {e}")

def check_uuid_format(table, column):
    print(f"\nChecking UUID format in {table}.{column}...")
    try:
        id_col = "run_id" if table == "client_analysis_runs" else "id"
        response = supabase.table(table).select(f"{id_col}, {column}").execute()
        invalid_uuids = []
        for item in response.data:
            val = item.get(column)
            if val:
                try:
                    uuid.UUID(str(val))
                except ValueError:
                    invalid_uuids.append((item[id_col], val))
        
        if invalid_uuids:
            print(f"❌ Found {len(invalid_uuids)} invalid UUIDs in {table}: {invalid_uuids}")
        else:
            print(f"✅ All values in {table}.{column} are valid UUIDs.")
    except Exception as e:
        print(f"Error checking UUIDs in {table}: {e}")

def main():
    print("Starting Data Audit...")
    client_ids = get_all_ids("clients")
    print(f"Found {len(client_ids)} clients.")

    if not client_ids:
        print("Warning: No clients found. Orphan checks might be misleading if child tables are not empty.")

    check_orphans("strategic_guardrails", "client_id", client_ids)
    check_orphans("midterm_plan_documents", "client_id", client_ids)
    check_orphans("client_datasets", "client_id", client_ids)
    check_orphans("client_analysis_runs", "client_id", client_ids)

    # Check UUID format specifically for strategic_guardrails if it might be TEXT
    check_uuid_format("strategic_guardrails", "client_id")

if __name__ == "__main__":
    main()
