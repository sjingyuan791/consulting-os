import json
import os
import time
import threading
import concurrent.futures
import logging
from openai import OpenAI
from core.config import Config
from core.llm_router import LLMRouter
from core.models import DiagnosisReport, StrategyResponse
from core.prompts import SYSTEM_PROMPT_SUMMARIZER, SYSTEM_PROMPT_DIAGNOSIS, get_final_prompt
from core.strategy_prompts import SYSTEM_PROMPT_STRATEGY
from typing import List, Dict, Any

# Rate limiting configuration
_rate_limit_lock = threading.Lock()
_last_request_time = 0
_MIN_REQUEST_INTERVAL = 0.1  # 100ms between requests (10 RPS max)

def _rate_limit():
    """Simple rate limiter to prevent API throttling."""
    global _last_request_time
    with _rate_limit_lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.time()

client = OpenAI(api_key=Config.OPENAI_API_KEY)

# --- Cost/Usage Tracking ---
# Model pricing (per 1K tokens, USD) - updated 2025/12
_MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "o1": {"input": 0.015, "output": 0.06},
}

def record_llm_usage(task_type: str, model: str, prompt_tokens: int, completion_tokens: int):
    """
    Records LLM usage metrics to Supabase (primary) or local JSON (fallback).
    Tracks token counts and estimated cost per call.
    """
    import datetime
    pricing = _MODEL_PRICING.get(model, {"input": 0.003, "output": 0.015})
    estimated_cost = (prompt_tokens / 1000 * pricing["input"]) + (completion_tokens / 1000 * pricing["output"])
    
    record = {
        "task_type": task_type,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "estimated_cost_usd": round(estimated_cost, 6),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    
    logger = logging.getLogger(__name__)
    logger.info(f"[LLM Usage] {task_type} | {model} | in:{prompt_tokens} out:{completion_tokens} | ${estimated_cost:.4f}")
    
    # Primary: Supabase
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        sb.table("llm_usage_log").insert(record).execute()
        return
    except Exception:
        pass  # Fallback to local JSON
    
    # Fallback: Local JSON file
    try:
        import os, json
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "artifacts_out")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "llm_usage_log.json")
        
        existing = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing.append(record)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug(f"LLM usage logging fallback failed: {e}")

def summarize_chunk(text_chunk: str) -> str:
    """Summarizes a text chunk."""
    model = LLMRouter.route("summary")
    _rate_limit()  # Apply rate limiting
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_SUMMARIZER},
                {"role": "user", "content": text_chunk}
            ]
        )
        
        # Track usage
        if response.usage:
            record_llm_usage("summary", model, response.usage.prompt_tokens, response.usage.completion_tokens)
            
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Summarization error: {type(e).__name__}")
        return "[要約処理でエラーが発生しました]"

def run_diagnosis(financial_json: dict, sales_json: dict, text_chunks: List[str]) -> DiagnosisReport:
    """
    Executes the full diagnosis flow:
    1. Summarize text chunks (Parallel Map-Reduce)
    2. Consolidate text summary (Reduce)
    3. Generate final report (Structured Output)
    """
    
    # 1. Text Summary (Parallel Map-Reduce)
    summaries = [None] * len(text_chunks)
    
    # Determine max workers (limit to avoid rate limits or CPU overload)
    max_workers = min(8, os.cpu_count() or 4)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(summarize_chunk, chunk): i 
            for i, chunk in enumerate(text_chunks)
        }
        
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                summaries[index] = future.result()
            except Exception as e:
                # Retry once logic could go here, but summarize_chunk handles exceptions reasonably
                summaries[index] = f"[Error in chunk {index}: {e}]"

    # Filter out potential Nones if something went totally wrong (unlikely with above logic)
    valid_summaries = [s for s in summaries if s]
    combined_text_summary = "\n\n".join(valid_summaries)
    
    # 2. Final Prompting
    final_user_prompt = get_final_prompt(
        financial_summary=json.dumps(financial_json, ensure_ascii=False, indent=2),
        sales_summary=json.dumps(sales_json, ensure_ascii=False, indent=2),
        text_summary=combined_text_summary
    )
    
    # 3. Structured Generation
    model = LLMRouter.route("diagnosis")
    try:
        completion = client.beta.chat.completions.parse(
            model=model, 
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_DIAGNOSIS},
                {"role": "user", "content": final_user_prompt}
            ],
            response_format=DiagnosisReport,
        )
        
        # Track usage (parsed response usage usually available in raw response but beta wrapper might differ)
        # Using usage from completion if available
        if completion.usage:
             record_llm_usage("diagnosis", model, completion.usage.prompt_tokens, completion.usage.completion_tokens)
             
        return completion.choices[0].message.parsed, combined_text_summary
    except Exception as e:
        import logging
        logging.error(f"Diagnosis LLM error: {type(e).__name__}", exc_info=True)
        raise RuntimeError("AI診断処理に失敗しました。データを確認してください。")

def summarize_history(history: List[dict]) -> str:
    """
    Summarizes older chat history to save tokens.
    """
    model = LLMRouter.route("summary")
    history_text = ""
    for h in history:
        content = h['content']
        # If content is dict, stringify
        if isinstance(content, dict) or (isinstance(content, object) and not isinstance(content, str)):
            content = json.dumps(content, ensure_ascii=False)
        history_text += f"{h['role']}: {content}\n"
        
    sys_prompt = "Summarize the following conversation history, extracting key facts, decisions, and current context. Keep it concise."
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": history_text}
            ]
        )
        if response.usage:
            record_llm_usage("history_summary", model, response.usage.prompt_tokens, response.usage.completion_tokens)
        return response.choices[0].message.content
    except Exception as e:
        import logging
        logging.debug(f"History summarization failed: {type(e).__name__}")
        return ""

def run_strategy_chat(history: List[dict], context_json: str) -> StrategyResponse:
    """
    Runs the chat with Strategy Consultant Persona.
    history: List of {"role": "user"|"assistant", "content": "..."}
    context_json: Stringified StrategyContext
    """
    
    # Task 6: Token Control
    MAX_HISTORY = 10
    
    final_history = []
    
    if len(history) > MAX_HISTORY:
        older_history = history[:-MAX_HISTORY]
        recent_history = history[-MAX_HISTORY:]
        
        # Summarize older history
        summary = summarize_history(older_history)
        
        # Inject summary as system/context
        summary_msg = f"\n[Previous Conversation Summary]\n{summary}"
        context_json = f"{context_json}\n{summary_msg}"
        final_history = recent_history
    else:
        final_history = history
    
    # System prompt enrichment
    system_msg = f"{SYSTEM_PROMPT_STRATEGY}\n\n[CONTEXT]\n{context_json}"
    
    messages = [{"role": "system", "content": system_msg}]
    messages.extend(final_history)
    
    model = LLMRouter.route("chat")
    try:
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=StrategyResponse,
            max_tokens=4096,
        )
        if completion.usage:
             record_llm_usage("strategy_chat", model, completion.usage.prompt_tokens, completion.usage.completion_tokens)
        return completion.choices[0].message.parsed
    except Exception as e:
        import logging
        logging.error(f"Strategy chat error: {type(e).__name__}", exc_info=True)
        raise RuntimeError("戦略チャット処理に失敗しました。しばらくしてから再試行してください。")

def generate_chapter_content(section_title: str, prompt: str, context_str: str) -> str:
    """
    Generates text content for a specific section of the Management Plan.
    """
    model = LLMRouter.route("chapter")
    system_msg = f"You are a professional Management Consultant aimed at writing a detailed, formal business plan.\n\n[CONTEXT]\n{context_str}"
    user_msg = f"Write the content for the section '{section_title}'.\nInstruction: {prompt}\n\nOutput strictly the content in Markdown format."
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=8192,
        )
        if response.usage:
             record_llm_usage("chapter_gen", model, response.usage.prompt_tokens, response.usage.completion_tokens)
        return response.choices[0].message.content
    except Exception as e:
        import logging
        logging.error(f"Chapter generation error: {type(e).__name__}")
        return "[コンテンツ生成でエラーが発生しました]"

def generate_monthly_review_analysis(review_json: str, context_str: str) -> str:
    """
    Generates a monthly review summary, hypothesis updates, and action suggestions.
    """
    model = LLMRouter.route("review")
    system_msg = "You are a Strategy Execution Partner. Analyze the monthly performance gaps and suggest course corrections.\n"
    user_msg = f"""
    [Context]
    {context_str}

    [Monthly Performance]
    {review_json}

    Please output a JSON with the following keys:
    - summary: Concise summary of performance and key issues.
    - updated_hypotheses: List of 3 refined refined hypotheses given new data.
    - suggested_actions: List of 3 priority actions for next month.
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            response_format={"type": "json_object"}
        )
        if response.usage:
             record_llm_usage("monthly_review", model, response.usage.prompt_tokens, response.usage.completion_tokens)
        return response.choices[0].message.content
    except Exception as e:
        return json.dumps({"summary": f"Error: {e}", "updated_hypotheses": [], "suggested_actions": []})

def generate_strategy_options(
    financial_health: Any,
    internal_capability: Any,
    external_intelligence: Any,
    diagnosis: Any,
    guardrails: Any
) -> Any:
    """
    Generates strategic options based on full analysis context.
    Uses LLM-compatible pure schema, then maps to app schema.
    Returns StrategyOptionsSchema.
    """
    from core.strategy_prompts import SYSTEM_PROMPT_STRATEGY_GENERATION_V2
    from core.schemas.llm_response_schemas import LLMStrategyOptionsResponse
    from core.schemas.strategy import StrategyOptionsSchema, StrategyOption

    model = LLMRouter.route("strategy")
    
    # helper to safe serialize
    def safe_json(obj):
        if hasattr(obj, "model_dump_json"):
            return obj.model_dump_json()
        if hasattr(obj, "dict"):
            return json.dumps(obj.dict(), ensure_ascii=False)
        return json.dumps(obj, default=str, ensure_ascii=False)

    context_str = f"""
    [Financial Health]
    {safe_json(financial_health)}

    [Internal Capability]
    {safe_json(internal_capability)}

    [External Intelligence]
    {safe_json(external_intelligence)}

    [Root Cause Diagnosis]
    {safe_json(diagnosis)}

    [Guardrails]
    {safe_json(guardrails)}
    """

    try:
        _rate_limit()
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_STRATEGY_GENERATION_V2},
                {"role": "user", "content": f"Based on the following context, generate the strategic options.\n\n{context_str}"}
            ],
            response_format=LLMStrategyOptionsResponse,
            max_tokens=8192,
        )
        
        if completion.usage:
             record_llm_usage("strategy_gen", model, completion.usage.prompt_tokens, completion.usage.completion_tokens)
        
        llm_result = completion.choices[0].message.parsed
        
        # Map LLM response to app schema
        app_options = []
        for opt in llm_result.options:
            app_options.append(StrategyOption(
                id=opt.id,
                name=opt.name,
                description=opt.description,
                rationale=opt.rationale,
                feasibility=opt.feasibility,
                impact=opt.impact,
                feasibility_score=opt.feasibility_score,
                impact_score=opt.impact_score,
                risk=opt.risk,
                time_horizon=opt.time_horizon,
            ))
        
        return StrategyOptionsSchema(
            selected_context_summary=llm_result.selected_context_summary,
            options=app_options,
            recommended_option_index=llm_result.recommended_option_index,
            so_what_recommendation=llm_result.so_what_recommendation,
        )
        
    except Exception as e:
        import logging
        logging.error(f"Strategy generation error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise RuntimeError(f"戦略オプションの生成に失敗しました: {type(e).__name__}: {str(e)}")

def assess_internal_capabilities_llm(
    financial_score: int,
    sales_strengths: List[str],
    resources: List[dict],
    doc_context: str
) -> Any:
    """
    Analyzes internal environment using LLM.
    Uses LLM-compatible pure schema, then maps to CapabilityMatrixSchema.
    """
    from core.strategy_prompts import SYSTEM_PROMPT_INTERNAL_CAPABILITY
    from core.schemas.llm_response_schemas import LLMCapabilityResponse
    from core.internal_capability import CapabilityMatrixSchema
    
    model = LLMRouter.route("analysis")

    context_str = f"""
    [Financial Score]
    {financial_score}

    [Sales Strengths]
    {json.dumps(sales_strengths, ensure_ascii=False)}

    [Resources]
    {json.dumps(resources, ensure_ascii=False)}

    [Internal Documents]
    {doc_context if doc_context else "No internal documents provided."}
    """

    try:
        _rate_limit()
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_INTERNAL_CAPABILITY},
                {"role": "user", "content": f"Analyze the following internal environment data:\n\n{context_str}"}
            ],
            response_format=LLMCapabilityResponse,
            max_tokens=4096,
        )
        
        if completion.usage:
             record_llm_usage("internal_analysis", model, completion.usage.prompt_tokens, completion.usage.completion_tokens)
        
        llm_result = completion.choices[0].message.parsed
        
        # Map to app schema
        return CapabilityMatrixSchema(
            core_competencies=llm_result.core_competencies,
            resource_gaps=llm_result.resource_gaps,
            sustainable_advantages=llm_result.sustainable_advantages,
            process_maturity=llm_result.process_maturity,
        )
        
    except Exception as e:
        import logging
        logging.error(f"Internal analysis LLM error: {type(e).__name__}: {str(e)}")
        raise e

def analyze_external_environment_llm(
    context_text: str,
    competitors_list: List[dict]
) -> Any:
    """
    Analyzes external environment using LLM.
    Uses LLM-compatible pure schema, then maps to MarketStructureSchema.
    """
    from core.strategy_prompts import SYSTEM_PROMPT_EXTERNAL_INTELLIGENCE
    from core.schemas.llm_response_schemas import LLMMarketStructureResponse
    from core.external_intelligence import MarketStructureSchema, CompetitorInfo
    
    model = LLMRouter.route("analysis")

    context_str = f"""
    [Competitors]
    {json.dumps(competitors_list, ensure_ascii=False) if competitors_list else "No competitor data provided."}

    [External Documents & Context]
    {context_text if context_text else "No external documents provided."}
    """

    try:
        _rate_limit()
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_EXTERNAL_INTELLIGENCE},
                {"role": "user", "content": f"Analyze the following external environment data:\n\n{context_str}"}
            ],
            response_format=LLMMarketStructureResponse,
            max_tokens=4096,
        )
        
        if completion.usage:
             record_llm_usage("external_analysis", model, completion.usage.prompt_tokens, completion.usage.completion_tokens)
        
        llm_result = completion.choices[0].message.parsed
        
        # Map to app schema
        app_competitors = []
        for c in llm_result.competitors:
            app_competitors.append(CompetitorInfo(
                name=c.name,
                market_share=c.market_share,
                strength=c.strength,
                weakness=c.weakness,
            ))
        
        return MarketStructureSchema(
            market_size_tam=llm_result.market_size_tam,
            market_growth_rate=llm_result.market_growth_rate,
            competitors=app_competitors,
            competitive_intensity=llm_result.competitive_intensity,
            key_trends=llm_result.key_trends,
            regulatory_risks=llm_result.regulatory_risks,
        )
        
    except Exception as e:
        import logging
        logging.error(f"External analysis LLM error: {type(e).__name__}: {str(e)}")
        raise e
