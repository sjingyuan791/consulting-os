from core.models import StrategyContext, DiagnosisReport, FinancialMetrics, SalesRecord
from typing import List, Dict, Any
import json

def generate_strategy_context(
    report: DiagnosisReport,
    financials: List[FinancialMetrics],
    sales_summary: Dict,
    text_summary: str = ""
) -> StrategyContext:
    """
    Distills the full diagnosis and raw data into a StrategyContext.
    """
    
    # 1. Financial Summary String
    # Take the latest year and growth
    fin_str = "No financial data available."
    if financials:
        latest = financials[-1]
        # Pydantic model access
        fin_str = f"Latest Year ({latest.year}): GP Mgn {latest.gross_profit_margin:.1%}, OP Mgn {latest.operating_profit_margin:.1%}."

    # 2. Sales Summary String
    sales_str = "No sales detail data."
    if sales_summary:
        top_cust = sales_summary.get('top_customers', [])
        top_names = [c['customer'] for c in top_cust[:3]]
        sales_str = f"Top Customers: {', '.join(top_names)}. Pareto Top 20% Share: {sales_summary.get('pareto_top_20_share',0):.1%}"

    # 3. Market Summary (from Qualitative text or Report)
    # Since we don't have explicit market data struct, we rely on report hints or text summary
    market_str = "Refer to qualitative data for market context."
    if text_summary:
        market_str = f"Extracted Context: {text_summary[:500]}..."

    # 4. KPI Tree (from Diagnosis Report)
    kpi_tree = report.causal_structure if report.causal_structure else {}

    # 5. Risks & Opps (Derived from Diagnosis Report)
    # Diagnosis has 'blind_spots' (risks/opps mixed) and 'mece_issues'
    risks = report.blind_spots + report.mece_issues
    opportunities = report.hypothesis # Treat hypotheses as potential growth opps for now

    return StrategyContext(
        company_summary="Client Company", # Name to be filled at runtime? Or generic.
        financial_summary=fin_str,
        sales_summary=sales_str,
        market_summary=market_str,
        kpi_tree=kpi_tree,
        risks=risks,
        opportunities=opportunities,
        additional_data_summary=""
    )
