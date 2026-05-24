"""
Dashboard Widgets Module
Fetches high-level metrics and summaries for the main dashboard (app.py).
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging

from core.supabase_client import get_supabase_client
from core.schemas.midterm_plan_schema import MidtermPlanDocument

logger = logging.getLogger(__name__)

def get_analysis_summary(client_id: str) -> Dict[str, Any]:
    """
    Fetches the latest analysis run summary.
    Returns dict with score, summary text, and date.
    """
    try:
        supabase = get_supabase_client()
        # Fetch latest strategy run (which contains the final analysis package)
        # Note: 'final_strategy_package' column might be named 'final_strategy_package_json' in DB
        # We try to fetch columns that likely contain the data
        response = supabase.table("strategy_runs") \
            .select("id, created_at, final_strategy_package_json, analysis_run_id") \
            .eq("client_id", client_id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if not response.data:
            # Fallback: Check if there are any analysis runs directly (if strategy run hasn't happened yet)
            # This is useful for "work in progress" states
            try:
                analysis_res = supabase.table("analysis_runs") \
                    .select("created_at, summary_json") \
                    .eq("client_id", client_id) \
                    .order("created_at", desc=True) \
                    .limit(1) \
                    .execute()
                
                if analysis_res.data:
                    a_data = analysis_res.data[0]
                    summary_json = a_data.get("summary_json") or {}
                    # Try to extract score from analysis run summary
                    score = summary_json.get("financial_health", {}).get("overall_health_score", 0)
                    summary_text = summary_json.get("executive_summary", "") or "分析データは存在しますが、戦略策定はまだ完了していません。"
                    return {
                        "score": score,
                        "summary": summary_text,
                        "created_at": a_data.get("created_at")
                    }
            except Exception as e_inner:
                logger.warning(f"Fallback fetch from analysis_runs failed: {e_inner}")
            
            return None

        data = response.data[0]
        
        # Primary Source: final_strategy_package_json
        package = data.get("final_strategy_package_json") or {}
        
        # Breakdown of package extraction
        fh = package.get("financial_health", {})
        score = fh.get("overall_health_score", 0)
        
        opts = package.get("strategy_options", {})
        summary = opts.get("selected_context_summary", "")
        if not summary:
            # Fallback to description of first option if summary is missing
            options = opts.get("options", [])
            if options:
                summary = options[0].get("description", "")
        
        # If score is 0, verify if we can get it from analysis_runs linked to this strategy run
        if score == 0 and data.get("analysis_run_id"):
             try:
                ar_id = data.get("analysis_run_id")
                ar_res = supabase.table("analysis_runs").select("summary_json").eq("id", ar_id).single().execute()
                if ar_res.data:
                    ar_summary = ar_res.data.get("summary_json", {})
                    score = ar_summary.get("financial_health", {}).get("overall_health_score", 0)
             except Exception:
                 pass

        return {
            "score": score,
            "summary": summary,
            "created_at": data.get("created_at")
        }

    except Exception as e:
        logger.error(f"Error fetching analysis summary: {e}")
        return None

def get_strategic_kpis(client_id: str) -> List[Dict[str, Any]]:
    """
    Fetches Strategic KPIs from the approved Mid-term Management Plan (Section 12).
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("midterm_plan_documents") \
            .select("document_json") \
            .eq("client_id", client_id) \
            .execute()

        if not response.data:
            return []

        doc_json = response.data[0].get("document_json", {})
        sections = doc_json.get("sections", [])
        
        # Find Section 12 (KPI Architecture)
        # Robustly check for section_id 12 (int or str)
        kpi_section = None
        for s in sections:
            sid = s.get("section_id")
            if str(sid) == "12":
                kpi_section = s
                break
        
        if not kpi_section:
            return []
            
        data = kpi_section.get("data", {})
        if not data:
            return []
            
        # extract strategic_kpis
        kpis = data.get("strategic_kpis", [])
        
        # Return top 3-4 for display
        return kpis[:4]

    except Exception as e:
        logger.error(f"Error fetching strategic KPIs: {e}")
        return []

def get_execution_progress(client_id: str) -> Dict[str, Any]:
    """
    Fetches the latest execution run and calculates progress.
    Falls back to Mid-term Plan (Section 11/13/15) if no execution run exists yet.
    """
    try:
        supabase = get_supabase_client()
        
        # 1. Try strategy_execution_runs first (Legacy/Official execution)
        # Get latest Strategy Run ID
        strat_res = supabase.table("strategy_runs") \
            .select("id") \
            .eq("client_id", client_id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
            
        if strat_res.data:
            strat_id = strat_res.data[0]['id']
            exec_res = supabase.table("strategy_execution_runs") \
                .select("execution_roadmap_json, created_at") \
                .eq("strategy_run_id", strat_id) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
                
            if exec_res.data:
                row = exec_res.data[0]
                roadmap = row.get("execution_roadmap_json", {})
                actions = roadmap.get("actions", [])
                
                if actions:
                    total = len(actions)
                    completed = sum(1 for a in actions if str(a.get("status", "")).lower() in ["done", "completed", "完了"])
                    in_progress = sum(1 for a in actions if str(a.get("status", "")).lower() in ["in_progress", "doing", "着手"])
                    progress = (completed / total) * 100 if total > 0 else 0
                    
                    status_label = "順調"
                    if progress < 10: status_label = "開始直後"
                    elif progress > 80: status_label = "完了間近"
                    
                    return {
                        "total": total,
                        "completed": completed,
                        "in_progress": in_progress,
                        "progress": progress,
                        "status_label": status_label,
                        "last_updated": row.get("created_at")
                    }

        # 2. Fallback: Estimate progress from Mid-term Plan Document
        # Count items in Section 15 (Action Plan) or Section 11/13
        plan_res = supabase.table("midterm_plan_documents") \
            .select("document_json, updated_at") \
            .eq("client_id", client_id) \
            .execute()
            
        if plan_res.data:
            doc = plan_res.data[0].get("document_json", {})
            sections = doc.get("sections", [])
            
            # Look for Section 15 (Detailed Action Plan) or Section 11 (Initiatives)
            # Rough proxy: Count bullet points or specific data structures?
            # Or just return "Plan Formulated" state 0% progress
            
            # Let's check Section 15 data if available
            # Note: Section 15 might be empty if only batch generated to 12. 
            # If so, just return "Plan Created"
            
            return {
                "total": 0,
                "completed": 0,
                "progress": 0.0,
                "status_label": "計画策定済", # Indicates plan exists but execution hasn't started
                "last_updated": plan_res.data[0].get("updated_at")
            }

        return None

    except Exception as e:
        logger.error(f"Error fetching execution progress: {e}")
        return None

def get_swot_data(client_id: str) -> Dict[str, Any]:
    """
    Fetches SWOT Analysis (Section 6) for the dashboard matrix.
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("midterm_plan_documents") \
            .select("document_json") \
            .eq("client_id", client_id) \
            .execute()

        if not response.data:
            return None

        doc_json = response.data[0].get("document_json", {})
        sections = doc_json.get("sections", [])
        
        # Find Section 6 (SWOT)
        swot_section = next((s for s in sections if str(s.get("section_id")) == "6"), None)
        
        if not swot_section:
            return None
            
        data = swot_section.get("data", {})
        if not data:
            return None
            
        return {
            "strengths": data.get("strengths", []),
            "weaknesses": data.get("weaknesses", []),
            "opportunities": data.get("opportunities", []),
            "threats": data.get("threats", [])
        }

    except Exception as e:
        logger.error(f"Error fetching SWOT data: {e}")
        return None

def get_key_goals(client_id: str) -> List[str]:
    """
    Fetches Vision Quantitative Goals (KGI) from Section 2.
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("midterm_plan_documents") \
            .select("document_json") \
            .eq("client_id", client_id) \
            .execute()

        if not response.data:
            return []

        doc_json = response.data[0].get("document_json", {})
        sections = doc_json.get("sections", [])
        
        # Find Section 2 (Vision)
        vision_section = next((s for s in sections if str(s.get("section_id")) == "2"), None)
        
        if not vision_section:
            return []
            
        data = vision_section.get("data", {})
        goals = data.get("quantitative_goals", [])
        
        # Ensure list of strings
        if isinstance(goals, list):
            return [str(g) for g in goals if g]
        return []

    except Exception as e:
        logger.error(f"Error fetching Key Goals (KGI): {e}")
        return []

def get_financial_plan_summary(client_id: str) -> Dict[str, Any]:
    """
    Fetches Financial Plan (Section 13) summary.
    Returns: { "base_year": int, "target_year_revenue": float, "target_year_profit": float, "cagr": float }
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("midterm_plan_documents") \
            .select("document_json") \
            .eq("client_id", client_id) \
            .execute()

        if not response.data:
            return None

        doc_json = response.data[0].get("document_json", {})
        sections = doc_json.get("sections", [])
        
        # Find Section 13 (Financials)
        fin_section = next((s for s in sections if str(s.get("section_id")) == "13"), None)
        
        if not fin_section:
            return None
            
        data = fin_section.get("data", {})
        if not data:
            return None
            
        projections = data.get("projections", [])
        if not projections:
            return None
            
        # Get last year (Target Year)
        # Sort by year just in case
        sorted_proj = sorted(projections, key=lambda x: x.get("year", 0))
        target_proj = sorted_proj[-1]
        
        return {
            "base_year": data.get("base_year"),
            "target_year": target_proj.get("year"),
            "revenue": target_proj.get("revenue"),
            "operating_profit": target_proj.get("operating_profit"),
            "revenue_cagr": data.get("revenue_cagr"),
            "profit_cagr": data.get("profit_cagr")
        }

    except Exception as e:
        logger.error(f"Error fetching Financial Plan summary: {e}")
        return None

def check_critical_issues(client_id: str) -> List[Dict[str, Any]]:
    """
    Checks for any critical QA issues in the plan.
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("midterm_plan_documents") \
            .select("quality_check_json") \
            .eq("client_id", client_id) \
            .execute()

        if not response.data:
            return []

        qa_json = response.data[0].get("quality_check_json", {})
        if not qa_json:
            return []
            
        return qa_json.get("critical_issues", [])

    except Exception as e:
        logger.error(f"Error fetching Critical Issues: {e}")
        return []
