from typing import Dict, Any, List, Optional
import json
import uuid
from core.supabase_client import get_supabase_client
from core.llm_client import run_strategy_chat # Reusing chat or specialized prompt function

class StrategyLearningEngine:
    """
    Evaluates the results of a Strategy Execution Cycle and generates
    new hypotheses for the next iteration.
    """
    
    def __init__(self):
        self.sb = get_supabase_client()

    def evaluate_strategy_effectiveness(
        self,
        strategy_run_id: str,
        execution_run_id: str,
        monitoring_run_id: str
    ) -> str:
        """
        Main entry point. Computes score, generates hypotheses, and records learning.
        Returns the ID of the new strategy_learning_record.
        """
        
        # 1. Fetch Context
        ctx = self._fetch_full_context(strategy_run_id, execution_run_id, monitoring_run_id)
        
        # 2. Compute Effectiveness Score & Delta
        score, kpi_delta = self._compute_effectiveness(ctx)
        
        # 3. Generate New Hypotheses (Learning)
        new_hypotheses = self._generate_hypotheses(ctx, score, kpi_delta)
        
        # 4. Persist Record
        record_id = self._persist_learning_record(
            strategy_run_id, execution_run_id, monitoring_run_id,
            score, kpi_delta, new_hypotheses, ctx
        )
        
        return record_id

    def _fetch_full_context(self, s_id, e_id, m_id):
        # simplified fetch
        s_run = self.sb.table("strategy_runs").select("*").eq("id", s_id).single().execute()
        e_run = self.sb.table("strategy_execution_runs").select("*").eq("id", e_id).single().execute()
        m_run = self.sb.table("monitoring_runs").select("*").eq("id", m_id).single().execute()
        
        return {
            "strategy": s_run.data,
            "execution": e_run.data,
            "monitoring": m_run.data
        }

    def _compute_effectiveness(self, ctx):
        # Logic: Compare actuals (monitoring) vs targets (execution assumed)
        monitor = ctx["monitoring"]
        actuals = monitor.get("kpi_actuals_json", {})
        
        # We need targets. They are in execution run or strategy decision.
        # execution_run has assumed_kpi_targets_json
        targets = ctx["execution"].get("assumed_kpi_targets_json", {})
        
        total_score = 0
        count = 0
        deltas = {}
        
        # Flatten and compare
        # Assumes structure { "2025": { "kpi_1": 100 } }
        for year, kpi_map in actuals.items():
            if year not in targets: continue
            
            target_map = targets[year]
            deltas[year] = {}
            
            for kpi, val in kpi_map.items():
                tgt = target_map.get(kpi)
                if tgt:
                    # Normalized Delta: (Actual - Target) / Target
                    if tgt != 0:
                        delta = (float(val) - float(tgt)) / float(tgt)
                    else:
                        delta = 0
                    
                    deltas[year][kpi] = delta
                    total_score += delta
                    count += 1
        
        # Aggregate Score (Average Delta)
        # Note: This is rudimentary. 
        final_score = (total_score / count) if count > 0 else 0.0
        
        return final_score, deltas

    def _generate_hypotheses(self, ctx, score, delta):
        # Heuristic generation based on score
        hypotheses = []
        
        if score < -0.1:
            hypotheses.append("Strategy is underperforming. Consider pivots in capital allocation.")
            hypotheses.append("Review external assumptions; market conditions may have shifted.")
        elif score > 0.1:
            hypotheses.append("Strategy is outperforming. Double down on current high-yield initiatives.")
            hypotheses.append("Accelerate timeline for Phase 2 investment.")
        else:
            hypotheses.append("Strategy is tracking within expected variance. Maintain course.")
            
        # Extract specific KPI failures
        for year, d_map in delta.items():
            for kpi, d_val in d_map.items():
                if d_val < -0.2:
                    hypotheses.append(f"Critical failure in {kpi} ({year}). Investigate root cause immediately.")
                    
        return hypotheses

    def _persist_learning_record(self, s_id, e_id, m_id, score, delta, hyps, ctx):
        payload = {
            "strategy_run_id": s_id,
            "execution_run_id": e_id,
            "monitoring_run_id": m_id,
            "effectiveness_score": score,
            "kpi_delta_json": delta,
            "generated_hypotheses_json": hyps,
            "evaluation_context_json": {
                "parent_run_id": ctx["strategy"].get("parent_strategy_run_id"),
                "guardrails_version": ctx["strategy"].get("meta_json", {}).get("guardrails_version_id")
            },
            "lineage_json": {
                "derived_from": "monitoring_gap_analysis"
            }
        }
        # Upsert (Ignore on Conflict)
        # We rely on the unique constraint on monitoring_run_id
        res = self.sb.table("strategy_learning_records").upsert(
            payload, 
            on_conflict="monitoring_run_id",
            ignore_duplicates=True
        ).execute()
        
        if res.data:
            return res.data[0]['id']
        else:
            # If ignore_duplicates=True and conflict, it returns empty data (in some client versions)
            # or we need to fetch the existing one.
            # Supabase-py behaviors vary. Let's try to fetch if empty.
            existing = self.sb.table("strategy_learning_records").select("id").eq("monitoring_run_id", m_id).single().execute()
            if existing.data:
                return existing.data['id']
            # Fallback
            return None

# Singleton
strategy_learning_engine = StrategyLearningEngine()
