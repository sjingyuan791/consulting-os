"""
Execution Repository - Supabase-backed persistence for execution layer.
Replaces the legacy ExecutionStore (local JSON files).
"""
from typing import Dict, List, Optional, Any
from core.supabase_client import get_supabase_client
from core.models import ActionItem, KPIItem, KPIActual, MonthlyReview, ExecutionState
import logging


class ExecutionRepo:
    """
    Repository for execution layer data (actions, KPIs, reviews).
    All data is persisted in Supabase, replacing local JSON storage.
    """
    
    def __init__(self):
        self.sb = get_supabase_client()
    
    # ==================== Actions ====================
    
    def get_actions(self, client_id: str) -> List[ActionItem]:
        """Get all actions for a client."""
        try:
            res = self.sb.table("execution_actions").select("*").eq("client_id", client_id).order("created_at", desc=False).execute()
            return [self._row_to_action(row) for row in res.data] if res.data else []
        except Exception as e:
            logging.error(f"Failed to get actions: {type(e).__name__}")
            return []
    
    def add_action(self, client_id: str, action: ActionItem, user_id: Optional[str] = None) -> Optional[str]:
        """Add a new action."""
        try:
            payload = {
                "client_id": client_id,
                "title": action.title,
                "objective": action.objective,
                "owner": action.owner,
                "due_date": action.due_date,
                "status": action.status,
                "priority": action.priority,
                "impact": action.impact,
                "effort": action.effort,
                "tags": action.tags,
                "created_by": user_id
            }
            res = self.sb.table("execution_actions").insert(payload).execute()
            return res.data[0]["id"] if res.data else None
        except Exception as e:
            logging.error(f"Failed to add action: {type(e).__name__}")
            return None
    
    def update_action(self, action_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing action."""
        try:
            self.sb.table("execution_actions").update(updates).eq("id", action_id).execute()
            return True
        except Exception as e:
            logging.error(f"Failed to update action: {type(e).__name__}")
            return False
    
    def delete_action(self, action_id: str) -> bool:
        """Delete an action."""
        try:
            self.sb.table("execution_actions").delete().eq("id", action_id).execute()
            return True
        except Exception as e:
            logging.error(f"Failed to delete action: {type(e).__name__}")
            return False
    
    def _row_to_action(self, row: Dict) -> ActionItem:
        """Convert database row to ActionItem model."""
        return ActionItem(
            id=str(row["id"])[:8],  # Keep short ID for UI compatibility
            title=row.get("title", ""),
            objective=row.get("objective", ""),
            owner=row.get("owner", ""),
            due_date=str(row.get("due_date", "")) if row.get("due_date") else "",
            status=row.get("status", "Not Started"),
            priority=row.get("priority", "Medium"),
            impact=row.get("impact", 3),
            effort=row.get("effort", 3),
            tags=row.get("tags", [])
        )
    
    # ==================== KPIs ====================
    
    def get_kpis(self, client_id: str) -> List[KPIItem]:
        """Get all KPIs for a client with their values."""
        try:
            # Fetch KPIs with their values in one query
            res = self.sb.table("execution_kpis").select(
                "*, execution_kpi_values(*)"
            ).eq("client_id", client_id).execute()
            
            kpis = []
            for row in res.data or []:
                kpi = self._row_to_kpi(row)
                # Populate targets and actuals from kpi_values
                for val in row.get("execution_kpi_values", []):
                    month = val.get("year_month")
                    if val.get("target_value") is not None:
                        kpi.targets[month] = float(val["target_value"])
                    if val.get("actual_value") is not None:
                        kpi.actuals[month] = KPIActual(year_month=month, value=float(val["actual_value"]))
                kpis.append(kpi)
            return kpis
        except Exception as e:
            logging.error(f"Failed to get KPIs: {type(e).__name__}")
            return []
    
    def add_kpi(self, client_id: str, kpi: KPIItem, user_id: Optional[str] = None) -> Optional[str]:
        """Add a new KPI definition."""
        try:
            payload = {
                "client_id": client_id,
                "name": kpi.name,
                "definition": kpi.definition,
                "unit": kpi.unit,
                "created_by": user_id
            }
            res = self.sb.table("execution_kpis").insert(payload).execute()
            return res.data[0]["id"] if res.data else None
        except Exception as e:
            logging.error(f"Failed to add KPI: {type(e).__name__}")
            return None
    
    def set_kpi_target(self, kpi_id: str, year_month: str, target_value: float) -> bool:
        """Set or update a KPI target for a specific month."""
        try:
            # Upsert: insert or update on conflict
            payload = {
                "kpi_id": kpi_id,
                "year_month": year_month,
                "target_value": target_value
            }
            self.sb.table("execution_kpi_values").upsert(
                payload, 
                on_conflict="kpi_id,year_month"
            ).execute()
            return True
        except Exception as e:
            logging.error(f"Failed to set KPI target: {type(e).__name__}")
            return False
    
    def set_kpi_actual(self, kpi_id: str, year_month: str, actual_value: float) -> bool:
        """Set or update a KPI actual value for a specific month."""
        try:
            payload = {
                "kpi_id": kpi_id,
                "year_month": year_month,
                "actual_value": actual_value
            }
            self.sb.table("execution_kpi_values").upsert(
                payload,
                on_conflict="kpi_id,year_month"
            ).execute()
            return True
        except Exception as e:
            logging.error(f"Failed to set KPI actual: {type(e).__name__}")
            return False
    
    def _row_to_kpi(self, row: Dict) -> KPIItem:
        """Convert database row to KPIItem model."""
        return KPIItem(
            id=str(row["id"])[:8],
            name=row.get("name", ""),
            definition=row.get("definition", ""),
            unit=row.get("unit", ""),
            targets={},
            actuals={}
        )
    
    # ==================== Reviews ====================
    
    def get_reviews(self, client_id: str) -> List[MonthlyReview]:
        """Get all monthly reviews for a client."""
        try:
            res = self.sb.table("execution_reviews").select("*").eq("client_id", client_id).order("year_month", desc=True).execute()
            return [self._row_to_review(row) for row in res.data] if res.data else []
        except Exception as e:
            logging.error(f"Failed to get reviews: {type(e).__name__}")
            return []
    
    def get_review(self, client_id: str, year_month: str) -> Optional[MonthlyReview]:
        """Get a specific monthly review."""
        try:
            res = self.sb.table("execution_reviews").select("*").eq("client_id", client_id).eq("year_month", year_month).execute()
            return self._row_to_review(res.data[0]) if res.data else None
        except Exception as e:
            logging.error(f"Failed to get review: {type(e).__name__}")
            return None
    
    def save_review(self, client_id: str, review: MonthlyReview, user_id: Optional[str] = None) -> bool:
        """Save or update a monthly review (upsert)."""
        try:
            payload = {
                "client_id": client_id,
                "year_month": review.year_month,
                "kpi_gaps_json": review.kpi_gaps,
                "alerts": review.alerts,
                "summary": review.summary,
                "updated_hypotheses": review.updated_hypotheses,
                "suggested_actions": review.suggested_actions,
                "created_by": user_id
            }
            self.sb.table("execution_reviews").upsert(
                payload,
                on_conflict="client_id,year_month"
            ).execute()
            return True
        except Exception as e:
            logging.error(f"Failed to save review: {type(e).__name__}")
            return False
    
    def _row_to_review(self, row: Dict) -> MonthlyReview:
        """Convert database row to MonthlyReview model."""
        return MonthlyReview(
            year_month=row.get("year_month", ""),
            kpi_gaps=row.get("kpi_gaps_json", {}),
            alerts=row.get("alerts", []),
            summary=row.get("summary", ""),
            updated_hypotheses=row.get("updated_hypotheses", []),
            suggested_actions=row.get("suggested_actions", [])
        )
    
    # ==================== Legacy Compatibility ====================
    
    def load_state(self, client_id: str) -> ExecutionState:
        """
        Load full execution state (legacy compatibility).
        Combines actions, KPIs, and reviews into ExecutionState.
        """
        return ExecutionState(
            client_id=client_id,
            actions=self.get_actions(client_id),
            kpis=self.get_kpis(client_id),
            reviews=self.get_reviews(client_id)
        )
    
    def save_action_update(self, client_id: str, action: ActionItem, user_id: Optional[str] = None):
        """
        Convenience method to add or update an action.
        Used during migration from ExecutionStore.
        """
        # Check if action exists by legacy ID pattern
        existing = self.sb.table("execution_actions").select("id").eq("client_id", client_id).ilike("id", f"{action.id}%").execute()
        
        if existing.data:
            # Update existing
            self.update_action(existing.data[0]["id"], {
                "title": action.title,
                "objective": action.objective,
                "owner": action.owner,
                "due_date": action.due_date,
                "status": action.status,
                "priority": action.priority,
                "impact": action.impact,
                "effort": action.effort,
                "tags": action.tags
            })
        else:
            # Insert new
            self.add_action(client_id, action, user_id)


# Singleton-like accessor
_execution_repo = None

def get_execution_repo() -> ExecutionRepo:
    """Get the singleton ExecutionRepo instance."""
    global _execution_repo
    if _execution_repo is None:
        _execution_repo = ExecutionRepo()
    return _execution_repo
