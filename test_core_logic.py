import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Add core to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

# Import core logic to test
try:
    from core.industry_benchmarks import get_benchmark, classify_company_size
except ImportError as e:
    print(f"Error importing core modules: {e}")
    exit(1)

load_dotenv()

# Use SERVICE KEY for this test (simulating authenticated app logic)
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Error: SUPABASE_SERVICE_KEY not found in .env (Required for logic test)")
    exit(1)

supabase: Client = create_client(url, key)

def test_logic():
    print("Starting Core Logic Check...")
    
    # 1. Fetch Test Client
    print("Fetching Test Client...")
    res = supabase.table("clients").select("*").eq("name", "Test Client - Seeding").execute()
    
    if not res.data:
        print("❌ Test Client not found. Seeding might have failed.")
        return
    
    client = res.data[0]
    client_id = client.get("id") or client.get("client_id")
    print(f"Found Client: {client.get('name')} (ID: {client_id})")
    
    # 2. Fetch Financials (Analysis Run)
    print("Fetching Analysis Run...")
    # runs uses run_id as PK but client_id FK
    res_runs = supabase.table("client_analysis_runs").select("*").eq("client_id", client_id).execute()
    
    revenue = 0
    if res_runs.data:
        run_data = res_runs.data[0]
        metrics = run_data.get("financial_metrics_json", {})
        revenue = metrics.get("revenue", 0)
        print(f"Found Financial Data: Revenue = {revenue}")
    else:
        print("⚠️ No analysis runs found. Using default revenue.")
    
    # 3. Test Core Logic (Industry Benchmarks)
    print("Testing Industry Benchmarks Logic...")
    
    # Determine size
    size = classify_company_size(revenue)
    print(f"Classified Size: {size}")
    
    # Get Benchmark
    # Client industry is 'Technology', benchmarking module uses 'it' mostly, let's see fallback
    industry = client.get("industry") or "generic"
    print(f"Client Industry: {industry}")
    
    # Map 'Technology' to 'it' for test if needed, or see if default works
    if industry.lower() == "technology":
        industry = "it"
        
    benchmark = get_benchmark(industry, size)
    
    print(f"Benchmark Result: {benchmark}")
    
    if benchmark:
        print("✅ Core Logic Test Passed: Benchmarks generated successfully.")
    else:
        print("❌ Core Logic Test Failed: No benchmark returned.")

if __name__ == "__main__":
    test_logic()
