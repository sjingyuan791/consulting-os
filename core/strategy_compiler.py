from typing import Dict, Any, Optional, List

def compile_strategy_context(
    financial_quality: Dict[str, Any], 
    sales_quality: Dict[str, Any], 
    financial_metrics: Optional[Dict[str, Any]] = None, 
    sales_metrics: Optional[Dict[str, Any]] = None,
    guardrails: Optional[Any] = None # GuardrailsSchema
) -> Dict[str, Any]:
    """
    Compiles a deterministic strategy context based on data quality and basic metrics.
    NO LLM calls here. Pure logic.
    """
    
    # Extract Strategic Principles from Guardrails
    strategic_principles = {
        "do": [],
        "do_not": [],
        "non_negotiables": []
    }
    
    if guardrails:
        # Pydantic or Dict check
        boundaries = getattr(guardrails, "strategic_boundaries", {}) if hasattr(guardrails, "strategic_boundaries") else guardrails.get("strategic_boundaries", {})
        
        strategic_principles["do"] = boundaries.get("must_haves", [])
        strategic_principles["do_not"] = boundaries.get("must_not_haves", [])
        
        # Non-negotiables
        risk = getattr(guardrails, "risk_tolerance", None) or guardrails.get("risk_tolerance")
        budget = getattr(guardrails, "investment_limit", None) or guardrails.get("investment_limit")
        
        if risk:
            strategic_principles["non_negotiables"].append(f"Risk Tolerance: {risk}")
        if budget:
            strategic_principles["non_negotiables"].append(f"Budget Cap: {budget}")

    context = {
        "data_health": {
            "financial_score": financial_quality.get("quality_score", 0),
            "sales_score": sales_quality.get("quality_score", 0),
            "overall_score": 0
        },
        "strategic_principles": strategic_principles,
        "risk_flags": [],
        "constraint_flags": [],
        "priority_focus": [],
        "recommended_analysis_next": [],
        "health_summary": ""
    }
    
    # 1. Calculate Overall Score
    f_score = context["data_health"]["financial_score"]
    s_score = context["data_health"]["sales_score"]
    context["data_health"]["overall_score"] = int((f_score + s_score) / 2)
    
    # 2. Assess Constraints based on Quality
    if f_score < 60:
        context["constraint_flags"].append("financial_data_low_reliability")
        context["risk_flags"].append("Financial analysis may be inaccurate due to data quality issues.")
        
    if s_score < 60:
        context["constraint_flags"].append("sales_data_low_reliability")
        context["risk_flags"].append("Sales analysis may be inaccurate due to data quality issues.")

    # 3. Assess Risks based on Data Content (if metrics provided)
    if sales_metrics:
        # Check customer concentration
        top1_share = sales_metrics.get("top1_share", 0)
        if top1_share > 0.3:
            context["risk_flags"].append("High Customer Concentration (Top 1 > 30%)")
            context["priority_focus"].append("concentration_mitigation")
            
        # Check Growth
        trend = sales_metrics.get("monthly_trend", [])
        if trend and len(trend) > 12:
            last_yoy = trend[-1].get("yoy_growth", 0)
            if last_yoy < -0.1:
                context["risk_flags"].append("Declining Sales Trend")
                context["priority_focus"].append("sales_recovery")

    if financial_metrics:
         # Mock check (assuming we had extracted profit margin in metrics)
         pass

    # 4. Determine Recommended Analysis
    if "concentration_mitigation" in context["priority_focus"]:
        context["recommended_analysis_next"].append("Pareto Analysis")
        context["recommended_analysis_next"].append("Customer Risk Assessment")
        
    if f_score >= 80 and s_score >= 80:
        context["recommended_analysis_next"].append("Integrated Profitability Analysis")
    else:
        context["recommended_analysis_next"].append("Data Cleansing & Validation")

    # 5. Generate Deterministic Summary
    summary_parts = []
    if context["data_health"]["overall_score"] >= 80:
        summary_parts.append("Data quality is robust.")
    elif context["data_health"]["overall_score"] >= 60:
        summary_parts.append("Data quality is acceptable but has minor issues.")
    else:
        summary_parts.append("Data quality is poor and requires attention.")
        
    if context["risk_flags"]:
        summary_parts.append(f"Identified {len(context['risk_flags'])} potential risks including: {', '.join(context['risk_flags'][:2])}.")
    
    context["health_summary"] = " ".join(summary_parts)
    
    return context

if __name__ == "__main__":
    # Example Usage Stub
    example_fin = {"quality_score": 75, "critical_flags": []}
    example_sales = {"quality_score": 50, "critical_flags": ["Missing Columns"]}
    example_sales_metrics = {"top1_share": 0.45}
    
    ctx = compile_strategy_context(example_fin, example_sales, sales_metrics=example_sales_metrics)
    print(ctx)
