from typing import Dict, Any, List, Optional
from core.schemas.monitoring import MonitoringRunSchema
from core.schemas.execution import GapAnalysisSchema
from core.supabase_client import get_supabase_client
import json

class ExecutionMonitoringEngine:
    def __init__(self):
        self.sb = get_supabase_client()

    def run_monitoring(self, execution_run_id: str, kpi_actuals: Dict[str, Dict[str, float]], user_id: str) -> Dict[str, Any]:
        """
        Compares Actuals vs Targets and generates Gap Analysis with Severity.
        Idempotent: If a COMPLETED run exists, return it.
        """
        
        # Check for existing COMPLETED run to ensure idempotency
        existing = self.sb.table("monitoring_runs").select("*").eq("execution_run_id", execution_run_id).eq("status", "COMPLETED").execute()
        if existing.data:
            return existing.data[0]

        # 1. Fetch Execution Context
        run_res = self.sb.table("strategy_execution_runs").select("*").eq("id", execution_run_id).single().execute()
        if not run_res.data:
            raise ValueError("Execution Run not found")
            
        run_data = run_res.data
        targets = run_data.get("assumed_kpi_targets_json", {})
        
        # 2. Compute Gaps
        gaps_result = self._compute_gaps(targets, kpi_actuals)
        
        # 3. Generate Analysis (Heuristic or LLM)
        analysis_pkg = self._generate_analysis(gaps_result)
        
        # 4. Store Monitoring Run
        # We might have a PENDING run. We should update it to COMPLETED, OR insert new one.
        # Given "Insert-Only" preference, creating a new COMPLETED row is cleaner for history 
        # IF we want to keep the PENDING record as "intent". 
        # However, typically PENDING transitions to COMPLETED.
        # Let's try to UPDATE the Pending one if it exists, matching the "Lifecycle" concept.
        
        pending = self.sb.table("monitoring_runs").select("id").eq("execution_run_id", execution_run_id).eq("status", "PENDING").execute()
        
        monitoring_payload = {
            "execution_run_id": execution_run_id,
            "kpi_actuals_json": kpi_actuals,
            "gap_analysis_json": analysis_pkg["text_analysis"],
            "severity": analysis_pkg["severity"],
            "priority": analysis_pkg["priority"],
            "structured_feedback_json": analysis_pkg["structured_feedback"],
            "created_by": user_id,
            "status": "COMPLETED",
            "meta_json": {
                "guardrails_version_id": run_data.get("meta_json", {}).get("guardrails_version_id")
            }
        }

        if pending.data:
            # Update the existing PENDING run
            res = self.sb.table("monitoring_runs").update(monitoring_payload).eq("id", pending.data[0]['id']).execute()
        else:
            # Insert new
            res = self.sb.table("monitoring_runs").insert(monitoring_payload).execute()
            
        monitoring_run = res.data[0]
        
        # 5. Trigger Strategy Learning (Auto-Evaluation)
        try:
            from core.strategy_learning_engine import strategy_learning_engine
            strat_id = run_data.get("strategy_run_id")
            if strat_id:
                strategy_learning_engine.evaluate_strategy_effectiveness(
                    strategy_run_id=strat_id,
                    execution_run_id=execution_run_id,
                    monitoring_run_id=monitoring_run["id"]
                )
        except Exception as e:
            import logging
            logging.error(f"Learning Engine Trigger Failed: {type(e).__name__}")

        return monitoring_run

    def _compute_gaps(self, targets, actuals):
        """Compute variance between targets and actuals."""
        gaps = {}
        for period, kpi_map in actuals.items():
            if period not in targets: continue
            period_targets = targets[period]
            gaps[period] = {}
            for kpi_id, actual_val in kpi_map.items():
                target_val = period_targets.get(kpi_id)
                if target_val is not None and target_val != 0:
                    variance = (float(actual_val) - float(target_val)) / float(target_val)
                    gaps[period][kpi_id] = variance
                else:
                    gaps[period][kpi_id] = 0.0
        return gaps

    def _generate_analysis(self, gaps_result):
        from core.schemas.monitoring import MonitoringFeedback
        
        alerts = []
        actions = []
        off_track_kpis = []
        severities = []
        rec_focus = []
        
        max_severity_val = 0 # 0=Minor, 1=Warning, 2=Critical
        
        for period, kpi_gaps in gaps_result.items():
            for kpi_id, variance in kpi_gaps.items():
                if variance < -0.2: # 20% Miss -> Critical
                    alerts.append(f"[{period}] CRITICAL Miss on {kpi_id}: {variance:.1%} below target")
                    actions.append(f"Immediate deep dive required for {kpi_id}")
                    off_track_kpis.append(kpi_id)
                    severities.append("CRITICAL")
                    max_severity_val = max(max_severity_val, 2)
                    
                elif variance < -0.1: # 10% Miss -> Warning
                    alerts.append(f"[{period}] WARNING on {kpi_id}: {variance:.1%} below target")
                    off_track_kpis.append(kpi_id)
                    severities.append("WARNING")
                    max_severity_val = max(max_severity_val, 1)
        
        if not alerts:
            alerts.append("On Track: All KPIs within acceptable range")
            max_severity_val = 0
            
        # Determine Overall Severity and Priority
        severity_map = {0: "MINOR", 1: "WARNING", 2: "CRITICAL"}
        overall_severity = severity_map[max_severity_val]
        
        # Priority (1=Highest)
        priority_score = 1 if overall_severity == "CRITICAL" else (3 if overall_severity == "WARNING" else 5)
        
        # Recommended Focus
        if off_track_kpis:
            rec_focus = list(set([k.split('_')[0] for k in off_track_kpis])) # Heuristic: 'sales_revenue' -> 'sales'
        
        structured_feedback = MonitoringFeedback(
            off_track_kpis=list(set(off_track_kpis)),
            severity=list(set(severities)),
            recommended_focus=rec_focus
        )
        
        text_analysis = {
            "summary": f"{overall_severity}: {len(alerts)} alerts generated.",
            "alerts": alerts,
            "recommended_actions": actions,
            "raw_gaps": gaps_result,
            "strategy_feedback_context": f"""
            [Monitoring Feedback]
            Severity: {overall_severity}
            Critical Gaps: {', '.join(off_track_kpis) if off_track_kpis else 'None'}
            Recommended Focus: {', '.join(rec_focus)}
            """
        }
        
        return {
            "text_analysis": text_analysis,
            "severity": overall_severity,
            "priority": priority_score,
            "structured_feedback": structured_feedback.model_dump()
        }


# Service Functions
def trigger_monitoring_run(execution_run_id: str, kpi_actuals: Dict[str, Any], user_id: str):
    """Triggers a monitoring run - convenience function."""
    engine = ExecutionMonitoringEngine()
    return engine.run_monitoring(execution_run_id, kpi_actuals, user_id)


def initialize_monitoring_run(execution_run_id: str, user_id: Optional[str] = None):
    """
    Creates a PENDING monitoring run. Idempotent.
    """
    sb = get_supabase_client()
    
    # Check if already exists (PENDING or COMPLETED)
    existing = sb.table("monitoring_runs").select("id").eq("execution_run_id", execution_run_id).execute()
    if existing.data:
        return  # Already initialized or completed
        
    payload = {
        "execution_run_id": execution_run_id,
        "status": "PENDING",
        "created_by": user_id,
        "kpi_actuals_json": {},
        "gap_analysis_json": {"summary": "Pending Data Collection"}
    }
    
    try:
        sb.table("monitoring_runs").insert(payload).execute()
    except Exception as e:
        import logging
        logging.warning(f"Monitoring Init Race Condition (Ignored): {type(e).__name__}")
