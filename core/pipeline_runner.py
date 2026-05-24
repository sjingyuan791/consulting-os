from typing import Dict, Any, List
import datetime
import json
import logging

# Schemas
from core.schemas.common import ModuleMeta, StrategyModuleSchema
from core.final_strategy_package import FinalStrategyPackageSchema

# Modules
from core.strategic_guardrails import define_guardrails, GuardrailsSchema
from core.external_intelligence import analyze_external_environment
from core.internal_capability import assess_internal_capabilities
from core.financial_engine import run_financial_engine
from core.root_cause_engine import build_issue_tree
from core.strategy_hypothesis import generate_strategy_hypotheses
from core.decision_layer import select_strategy

# from core.execution_design import design_execution_roadmap (De-coupled)
# from core.financial_simulation import simulate_outcome (De-coupled)

import pandas as pd
import logging

def _extract_sales_strengths(sales_data: Dict[str, Any]) -> List[str]:
    """
    Auto-extract sales strengths from transaction data.
    Analyzes patterns in the data to generate meaningful strength descriptions.
    """
    strengths = []
    transactions = sales_data.get("transactions", [])
    if not transactions:
        return strengths
    
    try:
        if isinstance(transactions, list) and len(transactions) > 0:
            df = pd.DataFrame(transactions)
            
            # Customer concentration analysis
            if "customer" in df.columns or "顧客名" in df.columns:
                cust_col = "customer" if "customer" in df.columns else "顧客名"
                unique_customers = df[cust_col].nunique()
                if unique_customers > 0:
                    strengths.append(f"顧客基盤: {unique_customers}社の取引先")
                    
                    # Repeat customer analysis
                    cust_counts = df[cust_col].value_counts()
                    repeat_customers = (cust_counts > 1).sum()
                    if repeat_customers > 0:
                        repeat_rate = repeat_customers / unique_customers * 100
                        strengths.append(f"リピート率: {repeat_rate:.0f}% ({repeat_customers}社がリピート)")
            
            # Revenue distribution
            amount_col = None
            for col in ["amount", "金額", "売上", "revenue"]:
                if col in df.columns:
                    amount_col = col
                    break
            
            if amount_col:
                df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce")
                total = df[amount_col].sum()
                if total > 0:
                    strengths.append(f"取引実績: 総額{total:,.0f}円")
                    
                    # Top customer concentration
                    if "customer" in df.columns or "顧客名" in df.columns:
                        cust_col = "customer" if "customer" in df.columns else "顧客名"
                        top_share = df.groupby(cust_col)[amount_col].sum().max() / total * 100
                        if top_share < 30:
                            strengths.append("顧客分散: 上位顧客への依存度が低い（リスク分散型）")
                        elif top_share > 50:
                            strengths.append(f"主要顧客: 上位顧客が売上の{top_share:.0f}%を占める（深い関係性）")
            
            # Product/service diversity
            for col in ["product", "商品名", "サービス", "品目"]:
                if col in df.columns:
                    products = df[col].nunique()
                    if products > 1:
                        strengths.append(f"商品多様性: {products}種類の商品・サービスを展開")
                    break
                    
    except Exception as e:
        logging.debug(f"Sales strength extraction failed: {e}")
    
    return strengths


def aggregate_meta(modules: List[StrategyModuleSchema]) -> ModuleMeta:
    """
    Aggregates metadata from all pipeline modules into a single package-level meta.
    """
    aggregated = ModuleMeta(
        generated_at=datetime.datetime.now().isoformat()
    )
    
    min_confidence = 1.0
    
    for m in modules:
        # Check if module has meta field (it should if it inherits from StrategyModuleSchema)
        if not hasattr(m, 'meta'):
            continue
            
        meta = m.meta
        # Merge dataset versions (latest wins if conflict, but should be consistent)
        aggregated.dataset_versions.update(meta.dataset_versions)
        
        # Merge lists
        aggregated.rules_fired.extend(meta.rules_fired)
        aggregated.missing_inputs.extend(meta.missing_inputs)
        aggregated.falsifiers.extend(meta.falsifiers)
        aggregated.evidence.extend(meta.evidence)
        
        # Track minimum confidence
        if meta.confidence_score < min_confidence:
            min_confidence = meta.confidence_score
            
    aggregated.confidence_score = min_confidence
    return aggregated

async def run_strategy_pipeline(
    client_context: Dict[str, Any],
    financial_df_latest: Any, # DataFrame
    sales_data_latest: Dict[str, Any],
    market_data: Dict[str, Any],
    dataset_versions: Dict[str, int]
) -> FinalStrategyPackageSchema:
    """
    Orchestrates the full consulting logic pipeline.
    Deterministic, version-aware, and auditable.
    """
    
    # --- Phase 1: Status & Constraints ---
    
    # 1. Guardrails
    # Check if 'guardrails' is in client_context (passed from UI)
    if "guardrails" in client_context and client_context["guardrails"]:
        # It should be a dict or Schema
        g_data = client_context["guardrails"]
        if isinstance(g_data, dict):
            guardrails = define_guardrails(existing_guardrails=GuardrailsSchema(**g_data))
        else:
            guardrails = g_data
    else:
        # Fallback (Legacy)
        constraints = client_context.get("constraints", {})
        guardrails = define_guardrails(
            must_haves=constraints.get("must_haves", []),
            must_not_haves=constraints.get("must_not_haves", []),
            timeline_months=constraints.get("timeline_months", 12)
        )
    
    guardrails.meta.dataset_versions = dataset_versions
    
    # 2. Financials
    financial_engine_output = run_financial_engine(financial_df_latest)
    financial_engine_output.meta.dataset_versions = dataset_versions
    # Extract just the latest health check for downstream consumption if needed, 
    # but the package expects FinancialHealthSchema? 
    # Wait, FinalStrategyPackageSchema expects FinancialHealthSchema at 'financial_health' field.
    # financial_engine_output returns FinancialEngineOutput schema.
    # We might need to adjust FinalStrategyPackageSchema or this mapping.
    # Let's adjust FinalStrategyPackageSchema to accept FinancialEngineOutput.
    # Actually, let's keep it simple: FinancialEngineOutput IS the output.
    
    # 3. External
    # Convert structured market_data JSON into readable text for LLM
    
    market_data_text = ""
    if market_data:
        # Extract structured data (excluding 'documents' which is handled separately)
        structured_parts = []
        for key, value in market_data.items():
            if key == "documents":
                continue
            if value is not None:
                if isinstance(value, (dict, list)):
                    structured_parts.append(f"[{key}]\n{json.dumps(value, ensure_ascii=False, indent=2)}")
                else:
                    structured_parts.append(f"[{key}]: {value}")
        market_data_text = "\n\n".join(structured_parts)
    
    external_docs = market_data.get("documents", [])
    
    # Extract competitors from various possible locations in market_data
    competitors_list = market_data.get("competitors", [])
    if not competitors_list and isinstance(market_data.get("industry_statistics"), dict):
        competitors_list = market_data.get("industry_statistics", {}).get("competitors", [])
    
    # RAG: Retrieve relevant external context
    rag_external_context = ""
    try:
        from core.rag_service import get_rag_service
        client_id = dataset_versions.get("_client_id", "")
        if client_id:
            rag_service = get_rag_service()
            rag_result = rag_service.get_context(
                client_id=client_id,
                query="外部環境 市場動向 競合他社 業界トレンド 規制リスク",
                max_tokens=5000
            )
            if rag_result:
                rag_external_context = rag_result
    except Exception as e:
        logging.debug(f"RAG external context retrieval skipped: {e}")
    
    # Combine all external context
    if rag_external_context:
        if isinstance(external_docs, list):
            external_docs.append({"content": rag_external_context, "source": "RAG検索結果"})
        elif isinstance(external_docs, dict):
            external_docs = [external_docs, {"content": rag_external_context, "source": "RAG検索結果"}]
    
    external = analyze_external_environment(
        market_data_text=market_data_text,
        competitors_list=competitors_list,
        external_documents=external_docs
    )
    external.meta.dataset_versions = dataset_versions
    
    # 4. Internal
    # Calculate score from financial engine output for internal capability input
    fin_score = financial_engine_output.overall_health_score if financial_engine_output.overall_health_score else 50
    
    # Update: Pass internal_documents
    internal_docs = sales_data_latest.get("documents", [])
    
    # RAG: Retrieve relevant internal context
    try:
        if client_id:
            rag_internal_context = rag_service.get_context(
                client_id=client_id,
                query="組織体制 人材育成 業務プロセス コアコンピタンス 強み 弱み",
                max_tokens=5000
            )
            if rag_internal_context:
                if isinstance(internal_docs, list):
                    internal_docs.append({"content": rag_internal_context, "source": "RAG検索結果"})
                elif isinstance(internal_docs, dict):
                    internal_docs = [internal_docs, {"content": rag_internal_context, "source": "RAG検索結果"}]
    except Exception as e:
        logging.debug(f"RAG internal context retrieval skipped: {e}")
    
    # Auto-extract sales strengths from transaction data
    sales_strengths = sales_data_latest.get("summary", {}).get("strengths", [])
    if not sales_strengths:
        sales_strengths = _extract_sales_strengths(sales_data_latest)
    
    internal = assess_internal_capabilities(
        financial_score=fin_score,
        sales_strengths=sales_strengths,
        resources=client_context.get("resources", []),
        internal_documents=internal_docs
    )
    internal.meta.dataset_versions = dataset_versions

    # --- Phase 2: Diagnosis ---
    
    # 5. Root Cause
    # 5. Root Cause
    diagnosis = await build_issue_tree(financial_engine_output, external, internal)
    diagnosis.meta.dataset_versions = dataset_versions
    
    # --- Phase 3: Strategy Formulation ---
    
    # 6. Hypotheses
    # Using LLM Generation with full context
    options = generate_strategy_hypotheses(
        financial_health=financial_engine_output,
        internal_capability=internal,
        external_intelligence=external,
        diagnosis=diagnosis,
        guardrails=guardrails
    )
    options.meta.dataset_versions = dataset_versions
    
    # 7. Decision (Selection) - MOVED TO DECISION WORKSPACE
    # [ARCHITECTURE RULE]
    # The pipeline MUST terminate at Strategy Options generation.
    # Decision selection and Execution planning are strictly human-in-the-loop processes
    # performed in the Decision Workspace and mapped via decision_execution_service.
    selected = None
    
    # --- Phase 4: Execution Planning ---
    # Execution generation is triggered only by decision_execution_service.run_execution_phase()
    
    roadmap = None
    simulation = None

    # --- Assembly & Aggregation ---
    
    all_modules = [
        guardrails, financial_engine_output, external, internal,
        diagnosis, options, selected, roadmap, simulation
    ]
    
    aggregated_meta = aggregate_meta(all_modules)
    
    return FinalStrategyPackageSchema(
        meta=aggregated_meta,
        guardrails=guardrails,
        financial_health=financial_engine_output, # Mapped field needs to match type
        external_intelligence=external,
        internal_capability=internal,
        root_cause_diagnosis=diagnosis,
        strategy_options=options,
        selected_strategy=selected,
        execution_roadmap=roadmap,
        financial_simulation=simulation
    )
