"""
外部環境分析エンジン — GPT-4o 単一呼び出しで戦略的外部環境分析を生成。
PEST / 5フォース入力を受け取り、事業影響・マクロ総括・業界収益構造を出力する。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from core.schemas.external_env_schema import (
    BusinessImpactItem,
    EnhancedFiveForces,
    EnhancedForceDetail,
    ExternalEnvAnalysis,
    IndustryProfitDriver,
    IndustryProfitStructure,
    MacroSummary,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """あなたはMcKinsey・BCGレベルの戦略コンサルタントです。
提供されたPEST分析・5フォース・市場概況データを基に、経営戦略立案に直結する外部環境分析を行ってください。

【絶対遵守ルール】
1. 汎用フレーズ（「機会を活かす」「脅威に対応する」等）を使わず、業界固有の具体的表現を使うこと
2. 「外部環境の本質」は経営判断の核心を突く1文に凝縮すること（50〜80字）
3. 業界収益構造は財務的視点（粗利率・固定費比率・回収サイクル）を含むこと
4. 5フォースの各フォースには「戦略的含意」を必ず含めること
5. すべての分析はクライアントの業種・規模・事業モデルに固有の内容にすること"""


def _parse_force(raw: dict) -> EnhancedForceDetail:
    score = raw.get("score", 3)
    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 3
    score = max(1, min(5, score))
    trend = raw.get("trend", "stable")
    if trend not in ("increasing", "stable", "decreasing"):
        trend = "stable"
    return EnhancedForceDetail(
        score=score,
        summary=raw.get("summary", ""),
        key_players=raw.get("key_players", []),
        trend=trend,
        strategic_implication=raw.get("strategic_implication", ""),
    )


def _parse_output(raw: dict) -> ExternalEnvAnalysis:
    impact_list = []
    for item in raw.get("business_impact", []):
        direction = item.get("direction", "positive")
        if direction not in ("positive", "negative", "mixed"):
            direction = "mixed"
        magnitude = item.get("magnitude", "medium")
        if magnitude not in ("high", "medium", "low"):
            magnitude = "medium"
        horizon = item.get("time_horizon", "medium_term")
        if horizon not in ("short_term", "medium_term", "long_term"):
            horizon = "medium_term"
        impact_list.append(BusinessImpactItem(
            axis=item.get("axis", ""),
            description=item.get("description", ""),
            direction=direction,
            magnitude=magnitude,
            time_horizon=horizon,
            evidence=item.get("evidence", ""),
        ))

    macro_raw = raw.get("macro_summary", {})
    macro = MacroSummary(
        tailwinds=macro_raw.get("tailwinds", []),
        headwinds=macro_raw.get("headwinds", []),
        price_setting_structure=macro_raw.get("price_setting_structure", ""),
        irreversible_conditions=macro_raw.get("irreversible_conditions", []),
        essence_of_environment=macro_raw.get("essence_of_environment", ""),
    )

    prof_raw = raw.get("industry_profit_structure", {})
    drivers = []
    for d in prof_raw.get("key_profit_drivers", []):
        imp = d.get("importance", "medium")
        if imp not in ("high", "medium", "low"):
            imp = "medium"
        drivers.append(IndustryProfitDriver(
            driver=d.get("driver", ""),
            importance=imp,
            description=d.get("description", ""),
        ))
    profit_structure = IndustryProfitStructure(
        revenue_model=prof_raw.get("revenue_model", ""),
        cost_structure_summary=prof_raw.get("cost_structure_summary", ""),
        key_profit_drivers=drivers,
        margin_benchmarks=prof_raw.get("margin_benchmarks", ""),
        value_chain_bottleneck=prof_raw.get("value_chain_bottleneck", ""),
        disruption_risk=prof_raw.get("disruption_risk", ""),
    )

    forces_raw = raw.get("enhanced_five_forces", {})
    attractiveness = forces_raw.get("overall_attractiveness", "中")
    if attractiveness not in ("高", "中", "低"):
        attractiveness = "中"
    enhanced_forces = EnhancedFiveForces(
        rivalry=_parse_force(forces_raw.get("rivalry", {})),
        new_entrants=_parse_force(forces_raw.get("new_entrants", {})),
        substitutes=_parse_force(forces_raw.get("substitutes", {})),
        supplier=_parse_force(forces_raw.get("supplier", {})),
        buyer=_parse_force(forces_raw.get("buyer", {})),
        overall_attractiveness=attractiveness,
        overall_comment=forces_raw.get("overall_comment", ""),
        structural_insight=forces_raw.get("structural_insight", ""),
    )

    return ExternalEnvAnalysis(
        business_impact=impact_list,
        macro_summary=macro,
        industry_profit_structure=profit_structure,
        enhanced_five_forces=enhanced_forces,
        confidence_score=float(raw.get("confidence_score", 0.8)),
    )


def _build_prompt(input_data: Dict[str, Any]) -> str:
    def _dump(obj) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=2) if obj else "（データなし）"

    return f"""以下のクライアント外部環境データを基に、戦略立案に直結する分析を生成してください。

## 会社・業種情報
{_dump(input_data.get("company_info"))}

## 市場概況
{_dump(input_data.get("market_overview"))}

## PEST分析（入力済みデータ）
{_dump(input_data.get("pest"))}

## 5フォース（既存データ）
{_dump(input_data.get("five_forces"))}

---
以下のJSON形式で分析結果を返してください:

{{
  "business_impact": [
    {{
      "axis": "需要・市場成長 / コスト・原価 / 競争環境 / 規制・制度 / 技術変化 のいずれか",
      "description": "当該クライアントへの具体的な事業影響（数値・固有名詞含む）",
      "direction": "positive または negative または mixed",
      "magnitude": "high または medium または low",
      "time_horizon": "short_term または medium_term または long_term",
      "evidence": "根拠となるPEST項目・数値・事実"
    }}
  ],
  "macro_summary": {{
    "tailwinds": ["追い風要因1（具体的・業種固有）", "追い風要因2", "追い風要因3"],
    "headwinds": ["向かい風要因1（具体的・業種固有）", "向かい風要因2"],
    "price_setting_structure": "この業界の価格決定メカニズムと価格交渉力の構造（2〜3文）",
    "irreversible_conditions": ["不可逆的変化1（技術・規制・消費者行動等）", "不可逆的変化2"],
    "essence_of_environment": "外部環境の本質を表す1文（50〜80字、経営判断の核心を突く内容）"
  }},
  "industry_profit_structure": {{
    "revenue_model": "この業界の主要収益モデル（取引形態・課金構造）",
    "cost_structure_summary": "固定費・変動費比率と主要コストドライバー",
    "key_profit_drivers": [
      {{"driver": "利益ドライバー名", "importance": "high または medium または low", "description": "具体的説明"}}
    ],
    "margin_benchmarks": "業界平均の粗利率・営業利益率の水準（数値）",
    "value_chain_bottleneck": "価値連鎖上の利益集中点または制約点",
    "disruption_risk": "ビジネスモデル破壊リスクとその発生源"
  }},
  "enhanced_five_forces": {{
    "rivalry": {{
      "score": 1〜5,
      "summary": "根拠付きの2〜3文の説明",
      "key_players": ["主要プレイヤー1", "プレイヤー2"],
      "trend": "increasing または stable または decreasing",
      "strategic_implication": "このフォースから導かれる戦略的含意（1文）"
    }},
    "new_entrants": {{同形式}},
    "substitutes": {{同形式}},
    "supplier": {{同形式}},
    "buyer": {{同形式}},
    "overall_attractiveness": "高 または 中 または 低",
    "overall_comment": "業界の総合的な収益性・魅力度（2〜3文）",
    "structural_insight": "5フォース構造から見た最重要戦略示唆（1文）"
  }},
  "confidence_score": 0.85
}}

【制約】
- business_impactは需要・コスト・競争・規制・技術の5軸を網羅すること（各1〜2項目）
- enhanced_five_forcesのscoreは既存5フォースデータと整合させること
- essence_of_environmentは「〜により、〜が決定的に重要になった」形式推奨"""


def run_external_env_analysis(input_data: Dict[str, Any]) -> ExternalEnvAnalysis:
    """
    GPT-4o を呼び出して外部環境の戦略分析を生成する。
    input_data: {"company_info": {...}, "market_overview": {...}, "pest": {...}, "five_forces": {...}}
    """
    from openai import OpenAI
    from core.config import Config
    from core.llm_client import record_llm_usage

    client = OpenAI(api_key=Config.OPENAI_API_KEY)
    prompt = _build_prompt(input_data)

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=5000,
    )

    if completion.usage:
        record_llm_usage(
            "external_env_analysis",
            "gpt-4o",
            completion.usage.prompt_tokens,
            completion.usage.completion_tokens,
        )

    raw = json.loads(completion.choices[0].message.content)
    return _parse_output(raw)
