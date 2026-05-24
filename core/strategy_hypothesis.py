from typing import List, Optional, Any
from core.schemas.strategy import StrategyOptionsSchema, StrategyOption

def generate_strategy_hypotheses(
    financial_health: Any,
    internal_capability: Any,
    external_intelligence: Any,
    diagnosis: Any, # IssueTree/DiagnosisReport
    guardrails: Any # GuardrailsSchema
) -> StrategyOptionsSchema:
    """
    Generates strategic options based on the full analysis context using LLM.
    """
    from core.llm_client import generate_strategy_options
    
    try:
        # Call LLM to generate options
        generated_schema = generate_strategy_options(
            financial_health=financial_health,
            internal_capability=internal_capability,
            external_intelligence=external_intelligence,
            diagnosis=diagnosis,
            guardrails=guardrails
        )
        return generated_schema
        
    except Exception as e:
        import logging
        logging.error(f"Strategy generation failed, falling back to heuristic: {e}")
        
        # Fallback Logic (Heuristic) - Only used on critical API failure
        options = []
        
        # Default Cost Strategy
        opt_cost = StrategyOption(
            id="opt-cost-fallback",
            name="【自動生成失敗】コスト構造の最適化",
            description=f"AI生成エラー: {str(e)}", # Expose error
            rationale="フォールバック表示",
            feasibility="中",
            impact="中",
            feasibility_score=5,
            impact_score=5,
            risk="生成エラー",
            time_horizon="短期"
        )
        options.append(opt_cost)

        return StrategyOptionsSchema(
            selected_context_summary=f"AI生成中にエラーが発生しました: {str(e)}",
            options=options,
            recommended_option_index=0
        )

if __name__ == "__main__":
    # Mock inputs
    opts = generate_strategy_hypotheses(None, None)
    print(opts.model_dump_json(indent=2))
