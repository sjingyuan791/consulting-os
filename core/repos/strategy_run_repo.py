from typing import Dict, Any, Optional
from core.supabase_client import get_supabase_client

class StrategyRunRepo:
    def __init__(self):
        self.supabase = get_supabase_client()

    def create_strategy_run(
        self,
        client_id: str,
        analysis_run_id: str,
        guardrails: Dict,
        final_strategy_package: Dict,
        meta: Dict = {},
        created_by: Optional[str] = None
    ) -> str:
        """
        Records a Strategy Formulation decision.
        Atomic update: Sets other strategy runs to is_current=False.
        """
        
        # 1. Archive old runs
        self.supabase.table("strategy_runs")\
            .update({"is_current": False})\
            .eq("client_id", client_id)\
            .execute()
            
        # 2. Insert new run
        payload = {
            "client_id": client_id,
            "analysis_run_id": analysis_run_id,
            "guardrails_json": guardrails,
            "final_strategy_package_json": final_strategy_package,
            "decision_log_json": final_strategy_package.get("selected_strategy", {}), # Extract selection logic
            "meta_json": meta,
            "created_by": created_by,
            "is_current": True
        }
        
        res = self.supabase.table("strategy_runs").insert(payload).execute()
        if res.data:
            return res.data[0]['id']
        return ""

    def get_strategy_run(self, run_id: str) -> Optional[Dict]:
        res = self.supabase.table("strategy_runs").select("*").eq("id", run_id).execute()
        return res.data[0] if res.data else None

    
    def get_current_strategy_run(self, client_id: str) -> Optional[Dict]:
        res = self.supabase.table("strategy_runs")\
            .select("*")\
            .eq("client_id", client_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        return res.data[0] if res.data else None

    # --- Chat Persistence ---

    def get_or_create_thread(self, strategy_run_id: str, created_by: Optional[str] = None) -> str:
        """
        Gets the latest thread for a run, or creates one if none exists.
        """
        # Try get existing
        res = self.supabase.table("strategy_chat_threads")\
            .select("id")\
            .eq("strategy_run_id", strategy_run_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if res.data:
            return res.data[0]['id']
        
        # Create new
        payload = {
            "strategy_run_id": strategy_run_id,
            "title": "Strategy Discussion",
            "created_by": created_by
        }
        res = self.supabase.table("strategy_chat_threads").insert(payload).execute()
        return res.data[0]['id']

    def add_message(self, thread_id: str, role: str, content: Any) -> bool:
        """
        Adds a message to the thread. Content handles dict/json automatically if column is jsonb.
        """
        payload = {
            "thread_id": thread_id,
            "role": role,
            "content": content
        }
        res = self.supabase.table("strategy_chat_messages").insert(payload).execute()
        return bool(res.data)

    def get_thread_history(self, thread_id: str) -> list:
        """
        Returns chronological list of messages.
        """
        res = self.supabase.table("strategy_chat_messages")\
            .select("*")\
            .eq("thread_id", thread_id)\
            .order("created_at", desc=False)\
            .execute()
        return res.data if res.data else []

    def update_strategy_options(self, run_id: str, new_options: list) -> bool:
        """
        Updates the strategy options within the final strategy package.
        """
        # 1. Fetch current package
        current = self.get_strategy_run(run_id)
        if not current: return False
        
        package = current.get("final_strategy_package_json", {})
        
        # 2. Update options
        if "strategy_options" not in package:
            package["strategy_options"] = {}
        
        package["strategy_options"]["options"] = new_options
        
        # 3. Save back
        res = self.supabase.table("strategy_runs")\
            .update({"final_strategy_package_json": package})\
            .eq("id", run_id)\
            .execute()
            
        return bool(res.data)
