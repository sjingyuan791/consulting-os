import os
import uuid
import json
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Prioritize Service Key for seeding to bypass RLS
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

def seed_data():
    print("Starting Database Seeding...")

    # 1. Seed Data Categories
    categories = [
        {'category_id': 'financial', 'category_name': 'Financial Data', 'category_name_ja': '財務データ', 'description': '決算書、借入、資金繰り等', 'sort_order': 1},
        {'category_id': 'internal', 'category_name': 'Internal Environment', 'category_name_ja': '内部環境データ', 'description': '従業員、顧客、商品等', 'sort_order': 2},
        {'category_id': 'external', 'category_name': 'External Environment', 'category_name_ja': '外部環境データ', 'description': '市場、競合、業界等', 'sort_order': 3}
    ]
    print("Seeding data_categories...")
    for cat in categories:
        try:
            supabase.table('data_categories').upsert(cat).execute()
        except Exception as e:
            print(f"Error upserting category {cat['category_id']}: {e}")

    # 2. Seed Dataset Types
    types = [
        {'type_id': 'financials', 'type_name': 'Financial Statements', 'type_name_ja': '決算書', 'category_id': 'financial', 'sample_file': '01_財務データ/決算書.csv', 'description': 'BS/PL全勘定科目', 'sort_order': 1},
        # Add a few more significant ones
        {'type_id': 'employees', 'type_name': 'Employee List', 'type_name_ja': '従業員一覧', 'category_id': 'internal', 'sample_file': '02_内部環境データ/従業員一覧.csv', 'description': '人員・給与', 'sort_order': 11}
    ]
    print("Seeding dataset_types...")
    for t in types:
        try:
            supabase.table('dataset_types').upsert(t).execute()
        except Exception as e:
            print(f"Error upserting type {t['type_id']}: {e}")

    # 3. Seed Test Client
    test_client_id = "00000000-0000-0000-0000-000000000001"
    
    print(f"Seeding Client: {test_client_id}...")
    
    # Try inserting with specific column names based on schema knowledge
    # Schema introspection revealed 'name' instead of 'client_name'
    client_payload = {
        'client_id': test_client_id,
        'name': 'Test Client - Seeding', # changed from client_name
        # 'industry': 'Technology', # might not exist, let's omit for safety or try catch
        'workspace_id': str(uuid.uuid4())
    }

    try:
        # We use 'client_id' as the conflict column for upsert
        data = supabase.table('clients').upsert(client_payload, on_conflict='client_id').execute()
        print("✅ Client upserted successfully.")
    except Exception as e:
        print(f"⚠️ First upsert attempt failed: {e}")
        # Fallback: maybe the PK is 'id' and column is 'name'
        client_payload['id'] = client_payload.pop('client_id')
        try:
            supabase.table('clients').upsert(client_payload).execute()
            print("✅ Client upserted (using 'id' column).")
        except Exception as e2:
            print(f"❌ Failed to seed client: {e2}")
            # Try one last time without workspace_id just in case
            try:
                msg = str(e2)
                if "workspace_id" in msg or "does not exist" in msg:
                    del client_payload['workspace_id']
                    supabase.table('clients').upsert(client_payload).execute()
                    print("✅ Client upserted (minimal columns).")
                else: 
                     return
            except Exception as e3:
                print(f"❌ Failed to seed client (minimal): {e3}")
                return

    # 4. Seed Child Tables
    
    # Client Datasets
    print("Seeding client_datasets...")
    try:
        ds_payload = {
            'client_id': test_client_id,
            'dataset_type': 'financials',
            'display_name': 'Test Financials',
            'file_name': 'test_financials.csv'
        }
        supabase.table('client_datasets').insert(ds_payload).execute() # Insert because dataset_id is auto-generated
        print("✅ client_datasets inserted.")
    except Exception as e:
        print(f"Error seeding client_datasets: {e}")

    # Client Analysis Runs
    print("Seeding client_analysis_runs...")
    try:
        run_payload = {
            'client_id': test_client_id,
           # run_id auto generated
           'financial_metrics_json': {'revenue': 1000}
        }
        supabase.table('client_analysis_runs').insert(run_payload).execute()
        print("✅ client_analysis_runs inserted.")
    except Exception as e:
        print(f"Error seeding client_analysis_runs: {e}")

    # Strategic Guardrails
    print("Seeding strategic_guardrails...")
    try:
        sg_payload = {
            'client_id': test_client_id,
            'mission_objective': 'To test the seeding process.',
            'time_horizon_years': 3,
            'risk_tolerance': 'medium'
        }
        supabase.table('strategic_guardrails').insert(sg_payload).execute()
        print("✅ strategic_guardrails inserted.")
    except Exception as e:
        print(f"Error seeding strategic_guardrails: {e}")

    # Midterm Plan Documents
    print("Seeding midterm_plan_documents...")
    try:
        mp_payload = {
            'client_id': test_client_id,
            'document_json': {'title': 'Test Plan', 'content': 'Lorem ipsum'}
        }
        # This table has a UNIQUE index on client_id, so we should upsert or delete first.
        # But 'id' is PK. 
        # Attempt insert, if fail, we catch.
        supabase.table('midterm_plan_documents').insert(mp_payload).execute()
        print("✅ midterm_plan_documents inserted.")
    except Exception as e:
        print(f"Error seeding midterm_plan_documents: {e}")

if __name__ == "__main__":
    seed_data()
