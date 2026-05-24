"""
Stage 4: Strategy Design Engine — GPT-4o driven, client-specific.
All output is derived from actual client data (financials, SWOT, root cause, vision).
No hardcoded templates.
"""
from typing import Dict, Any, Optional, List
from core.pipeline.base_engine import AIEngine, EngineConfig
from core.schemas.pipeline_stages import (
    Stage4Output, CorporateStrategy, DomainStrategy, FunctionalStrategy,
    RiskAssessment, RiskItem,
)
import json
import logging

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """あなたはMcKinsey・BCGレベルの戦略コンサルタントです。
提供されたクライアント固有の情報（財務データ、SWOT分析、真因分析、ビジョン・ミッション等）を
厳密に参照し、テンプレートや一般論ではなくクライアント固有の戦略を設計してください。

【絶対遵守ルール】
1. すべての戦略提言はエビデンス（財務数値・内部分析・外部環境）に基づくこと
2. 「顧客価値の最大化」「持続的成長」「ステークホルダーとの共存」等の汎用フレーズ使用禁止
3. 機能別戦略の最優先機能は真因分析の根本課題に直結させること
4. リスクはクライアントの具体的状況（財務・市場・組織）に基づく内容にすること
5. 数値目標は財務データから導出した現実的な数値を使うこと"""


def _parse_risk_items(lst: list) -> List[RiskItem]:
    result = []
    for r in lst:
        prob = r.get("probability", "medium")
        imp = r.get("impact", "medium")
        if prob not in ("high", "medium", "low"):
            prob = "medium"
        if imp not in ("high", "medium", "low"):
            imp = "medium"
        result.append(RiskItem(
            id=r.get("id", "risk"),
            description=r.get("description", ""),
            probability=prob,
            impact=imp,
            mitigation_strategy=r.get("mitigation_strategy", ""),
        ))
    return result


def _parse_output(raw: dict) -> Stage4Output:
    corp = raw.get("corporate_strategy", {})
    pd = corp.get("portfolio_direction", "maintain")
    if pd not in ("growth", "maintain", "harvest", "divest"):
        pd = "maintain"

    corporate = CorporateStrategy(
        vision=corp.get("vision", ""),
        mission=corp.get("mission", ""),
        strategic_intent=corp.get("strategic_intent", ""),
        core_values=corp.get("core_values", []),
        portfolio_direction=pd,
        resource_allocation_priority=corp.get("resource_allocation_priority", []),
        long_term_goals=corp.get("long_term_goals", []),
    )

    domains = []
    for d in raw.get("domain_strategies", []):
        st_type = d.get("strategic_type", "differentiation")
        if st_type not in ("cost_leadership", "differentiation", "focus", "hybrid"):
            st_type = "differentiation"
        gs = d.get("growth_strategy", "market_penetration")
        if gs not in ("market_penetration", "market_development", "product_development", "diversification"):
            gs = "market_penetration"
        domains.append(DomainStrategy(
            domain_id=d.get("domain_id", "domain_1"),
            domain_name=d.get("domain_name", ""),
            competitive_position=d.get("competitive_position", ""),
            strategic_type=st_type,
            target_segments=d.get("target_segments", []),
            value_proposition=d.get("value_proposition", ""),
            competitive_advantages=d.get("competitive_advantages", []),
            growth_strategy=gs,
            key_success_factors=d.get("key_success_factors", []),
        ))

    funcs = []
    valid_funcs = ("sales", "marketing", "operations", "finance", "hr", "rd", "it")
    for f in raw.get("functional_strategies", []):
        fn = f.get("function", "operations")
        if fn not in valid_funcs:
            fn = "operations"
        funcs.append(FunctionalStrategy(
            function_id=f.get("function_id", f"func_{fn}"),
            function=fn,
            function_name_ja=f.get("function_name_ja", ""),
            objectives=f.get("objectives", []),
            key_initiatives=f.get("key_initiatives", []),
            resource_requirements=f.get("resource_requirements", {}),
            success_metrics=f.get("success_metrics", []),
            timeline=f.get("timeline", "Year 1-2"),
        ))

    risk = None
    risk_raw = raw.get("risk_assessment")
    if risk_raw:
        rl = risk_raw.get("overall_risk_level", "medium")
        if rl not in ("high", "medium", "low"):
            rl = "medium"
        risk = RiskAssessment(
            strategic_risks=_parse_risk_items(risk_raw.get("strategic_risks", [])),
            operational_risks=_parse_risk_items(risk_raw.get("operational_risks", [])),
            financial_risks=_parse_risk_items(risk_raw.get("financial_risks", [])),
            overall_risk_level=rl,
        )

    return Stage4Output(
        corporate_strategy=corporate,
        domain_strategies=domains,
        functional_strategies=funcs,
        strategy_rationale=raw.get("strategy_rationale", ""),
        risk_assessment=risk,
        confidence_score=float(raw.get("confidence_score", 0.8)),
    )


class StrategyDesignEngine(AIEngine[Dict[str, Any], Stage4Output]):
    """GPT-4o driven strategy design. Requires client-specific context in input_data."""

    STAGE_NUMBER = 4
    STAGE_NAME = "Strategy Design Engine"

    async def process(
        self,
        input_data: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Stage4Output:
        from openai import OpenAI
        from core.config import Config
        from core.llm_router import LLMRouter
        from core.llm_client import record_llm_usage

        prompt = self.build_prompt(input_data, previous_output)
        oa_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        model = LLMRouter.route("strategy")

        completion = oa_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=4096,
        )

        if completion.usage:
            record_llm_usage(
                "strategy_design",
                model,
                completion.usage.prompt_tokens,
                completion.usage.completion_tokens,
            )

        raw = json.loads(completion.choices[0].message.content)
        return _parse_output(raw)

    def build_prompt(
        self,
        input_data: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]] = None,
    ) -> str:
        def _dump(obj) -> str:
            return json.dumps(obj, ensure_ascii=False, indent=2) if obj else "（データなし）"

        guardrails = input_data.get("guardrails") or {}
        guardrails_note = ""
        if guardrails:
            boundaries = guardrails.get("strategic_boundaries", {})
            no_entry = boundaries.get("no_entry_markets", [])
            excl = boundaries.get("excluded_models", [])
            guardrails_note = f"""
## 戦略的ガードレール【必須制約 — 絶対に違反しないこと】
- ミッション目標: {guardrails.get("mission_objective", "未設定")}
- 計画期間: {guardrails.get("time_horizon_years", 3)}年
- 最大投資可能額: {guardrails.get("investment_limit", 0):.0f}百万円（この上限を超える投資提言は禁止）
- リスク許容度: {guardrails.get("risk_tolerance", "medium")}（超過リスクの戦略は採用しない）
- 参入禁止市場: {", ".join(no_entry) if no_entry else "なし"}
- 除外ビジネスモデル: {", ".join(excl) if excl else "なし"}
- 成功の定義: {guardrails.get("success_state_definition", "未設定")}
"""

        seg_eval = input_data.get("segment_evaluation")
        seg_note = ""
        if seg_eval:
            segs = seg_eval.get("segments", [])
            if segs:
                top = next((s for s in segs if s.get("priority_rank") == 1), segs[0])
                seg_lines = "\n".join(
                    f'  - #{s.get("priority_rank","?")} {s.get("segment_name","")} '
                    f'(スコア:{s.get("total_score",0):.1f}, 推奨:{s.get("recommendation","")})'
                    for s in sorted(segs, key=lambda x: x.get("priority_rank", 99))
                )
                seg_note = f"""
## セグメント評価（STEP 10で採点済み）
{seg_lines}
最優先セグメント: {top.get("segment_name","")} — {top.get("strategic_rationale","")}
※ domain_strategiesはこのセグメント優先順位と整合させること。
"""

        return f"""以下のクライアント固有情報を基に、具体的かつエビデンスに基づいた階層型戦略を設計してください。
{guardrails_note}{seg_note}
## 会社情報
{_dump(input_data.get("company_info"))}

## ビジョン・ミッション（STEP 7で確定済み）
{_dump(input_data.get("vision_mission"))}

## 財務サマリー（STEP 4で分析済み）
{_dump(input_data.get("financial_summary"))}

## SWOT分析（STEP 8で確定済み）
{_dump(input_data.get("swot"))}

## 内部環境調査結果（STEP 5-6で収集済み）
{_dump(input_data.get("internal_findings"))}

## 外部環境（STEP 2で登録済み）
{_dump(input_data.get("external_env"))}

## 真因分析（STEP 9で確定済み）
{_dump(input_data.get("root_cause"))}

---
以下のJSON形式で戦略を返してください。すべての文言はクライアント固有の内容にすること。

{{
  "corporate_strategy": {{
    "vision": "ビジョン（既存ビジョンがあればそれを尊重しつつ戦略と整合させる）",
    "mission": "ミッション（既存ミッションがあればそれを尊重しつつ戦略と整合させる）",
    "strategic_intent": "真因課題に直結した具体的な戦略意図（汎用表現禁止・数値含む）",
    "core_values": ["価値観1", "価値観2", "価値観3"],
    "portfolio_direction": "growth または maintain または harvest または divest",
    "resource_allocation_priority": ["優先度1（具体的）", "優先度2", "優先度3"],
    "long_term_goals": ["数値目標を含む具体的ゴール×3〜5"]
  }},
  "domain_strategies": [
    {{
      "domain_id": "domain_1",
      "domain_name": "クライアントの実際の事業ドメイン名",
      "competitive_position": "具体的な競合ポジション",
      "strategic_type": "cost_leadership または differentiation または focus または hybrid",
      "target_segments": ["ターゲット顧客セグメント"],
      "value_proposition": "クライアント固有の価値提案（汎用禁止）",
      "competitive_advantages": ["強み1", "強み2", "強み3"],
      "growth_strategy": "market_penetration または market_development または product_development または diversification",
      "key_success_factors": ["KSF1", "KSF2", "KSF3"]
    }}
  ],
  "functional_strategies": [
    {{
      "function_id": "func_<種別>",
      "function": "sales または marketing または operations または finance または hr または rd または it",
      "function_name_ja": "機能名（日本語）",
      "objectives": ["真因課題直結の目標×3（数値含む）"],
      "key_initiatives": ["具体的施策×3（当該クライアント固有）"],
      "resource_requirements": {{"人員": "具体的な必要人員・役割", "予算": "規模感", "システム": "必要システム"}},
      "success_metrics": ["数値KPIを含む指標×2"],
      "timeline": "Year 1 または Year 1-2 または Year 2-3"
    }}
  ],
  "strategy_rationale": "財務データ・真因分析のエビデンスに基づく戦略の根拠説明（300字以上）",
  "risk_assessment": {{
    "strategic_risks": [
      {{"id": "risk_s1", "description": "クライアント固有の戦略リスク", "probability": "high または medium または low", "impact": "high または medium または low", "mitigation_strategy": "具体的な対策"}}
    ],
    "operational_risks": [
      {{"id": "risk_o1", "description": "クライアント固有のオペレーションリスク", "probability": "medium", "impact": "high", "mitigation_strategy": "具体的な対策"}}
    ],
    "financial_risks": [
      {{"id": "risk_f1", "description": "クライアント固有の財務リスク", "probability": "medium", "impact": "medium", "mitigation_strategy": "具体的な対策"}}
    ],
    "overall_risk_level": "high または medium または low"
  }},
  "confidence_score": 0.85
}}

【制約】
- functional_strategiesは真因分析の根本課題に基づき最重要機能から3〜5機能を選択
- すべての目標・施策はクライアントの業界・規模・財務状況・課題に固有の内容
- portfolio_directionは財務サマリーとSWOT強み/弱みから論理的に導出すること"""


def create_strategy_engine(config: Optional[EngineConfig] = None) -> StrategyDesignEngine:
    return StrategyDesignEngine(config)
