from typing import Dict, Any, Optional
from core.supabase_client import get_supabase_client

class AnalysisRunRepo:
    def __init__(self):
        self.supabase = get_supabase_client()

    def create_analysis_run(
        self,
        client_id: str,
        dataset_version_set: Dict[str, str], # {"financial": uuid, "internal": uuid}
        pipeline_version: str = "v1.0",
        financial_metrics: Dict = {},
        sales_metrics: Dict = {},
        external_intelligence: Dict = {},
        internal_capability: Dict = {},
        created_by: Optional[str] = None
    ) -> str:
        """
        Records an execution of the Analysis Pipeline.
        """
        payload = {
            "client_id": client_id,
            "dataset_version_set": dataset_version_set,
            "pipeline_version": pipeline_version,
            "financial_metrics_json": financial_metrics,
            "sales_metrics_json": sales_metrics,
            "external_intelligence_json": external_intelligence,
            "internal_capability_json": internal_capability,
            "created_by": created_by
        }
        
        res = self.supabase.table("analysis_runs").insert(payload).execute()
        if res.data:
            return res.data[0]['id']
        return ""

    def get_analysis_run(self, run_id: str) -> Optional[Dict]:
        res = self.supabase.table("analysis_runs").select("*").eq("id", run_id).execute()
        return res.data[0] if res.data else None

    def get_latest_run(self, client_id: str) -> Optional[Dict]:
        res = self.supabase.table("analysis_runs")\
            .select("*")\
            .eq("client_id", client_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        return res.data[0] if res.data else None
