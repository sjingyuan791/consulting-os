import datetime
from typing import Dict, Any

# Repositories
from core.repos.dataset_repo import DatasetRepo
from core.repos.analysis_run_repo import AnalysisRunRepo
from core.repos.strategy_run_repo import StrategyRunRepo

# Pipeline
from core.pipeline_runner import run_strategy_pipeline

def run_lifecycle_example(client_id: str, financial_data: Any, sales_data: Dict, market_data: Dict):
    """
    Demonstrates the full lifecycle of a strategy run with persistence.
    """
    print(f"Starting Lifecycle for Client: {client_id}")

    # --- Step 1: Ingest & Version Datasets ---
    print("1. Versioning Datasets...")
    dataset_repo = DatasetRepo()
    
    # Financials
    # In reality, you'd pass the actual parsed JSON and Quality results here
    v_fin = dataset_repo.save_dataset_version(
        client_id=client_id,
        dataset_type="financial",
        normalized_json=financial_data.to_dict() if hasattr(financial_data, 'to_dict') else {},
        quality_json={"score": 95},
        source_type="upload"
    )
    print(f"  - Financial Dataset Version: {v_fin}")
    
    # Internal (Sales)
    v_int = dataset_repo.save_dataset_version(
        client_id=client_id,
        dataset_type="internal",
        normalized_json=sales_data,
        quality_json={"score": 88},
        source_type="upload"
    )
    print(f"  - Internal Dataset Version: {v_int}")
    
    # External (Market)
    v_ext = dataset_repo.save_dataset_version(
        client_id=client_id,
        dataset_type="external",
        normalized_json=market_data,
        quality_json={"score": 100},
        source_type="manual"
    )
    print(f"  - External Dataset Version: {v_ext}")
    
    dataset_versions = {
        "financial": v_fin,
        "internal": v_int,
        "external": v_ext
    }

    # --- Step 2: Run Pipeline (Pure Compute) ---
    print("2. Running Strategy Pipeline...")
    
    client_context = {"risk_tolerance": "Medium", "constraints": {"budget": 50000}}
    
    package = run_strategy_pipeline(
        client_context=client_context,
        financial_df_latest=financial_data,
        sales_data_latest=sales_data,
        market_data=market_data,
        dataset_versions=dataset_versions
    )
    
    print(f"  - Pipeline Complete. Confidence: {package.meta.confidence_score}")
    print(f"  - Selected Strategy: {package.selected_strategy.chosen_option_id}")

    # --- Step 3: Persist Analysis Run ---
    print("3. Persisting Analysis Run...")
    analysis_repo = AnalysisRunRepo()
    
    run_id = analysis_repo.create_analysis_run(
        client_id=client_id,
        dataset_version_set=dataset_versions,
        financial_metrics=package.financial_health.dict(),
        sales_metrics=package.internal_capability.dict(), # Simplified mapping
        external_intelligence=package.external_intelligence.dict(),
        internal_capability=package.internal_capability.dict()
    )
    print(f"  - Analysis Run ID: {run_id}")

    # --- Step 4: Persist Strategy Decision ---
    print("4. Persisting Strategy Decision...")
    strategy_repo = StrategyRunRepo()
    
    strategy_run_id = strategy_repo.create_strategy_run(
        client_id=client_id,
        analysis_run_id=run_id,
        guardrails=package.guardrails.dict(),
        final_strategy_package=package.dict(),
        meta=package.meta.dict()
    )
    print(f"  - Strategy Run ID: {strategy_run_id}")
    print("Lifecycle Complete!")
    return strategy_run_id

if __name__ == "__main__":
    # Dummy Data for Testing
    import pandas as pd
    
    dummy_cid = "00000000-0000-0000-0000-000000000000" # Needs a valid UUID if FK enforced, checking schema...
    # Clients table requires a valid UUID. If 'verify_supabase.py' didn't create one, this might fail on FK.
    # But for illustration, this is the code structure.
    
    # Simple check if we have a client, else create one (for the test)
    from core.supabase_client import get_supabase_client
    sb = get_supabase_client()
    res = sb.table("clients").select("id").limit(1).execute()
    if res.data:
        dummy_cid = res.data[0]['id']
    else:
        # Create a dummy client
        res = sb.table("clients").insert({"name": "Integration Test Corp"}).execute()
        dummy_cid = res.data[0]['id']
        
    df_dummy = pd.DataFrame({"売上": [100, 120], "営業利益": [10, 15], "総資産": [200, 220]})
    run_lifecycle_example(dummy_cid, df_dummy, {"summary": {"growth": 0.2}}, {"segments": []})
