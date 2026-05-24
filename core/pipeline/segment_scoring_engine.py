"""
セグメント評価エンジン — GPT-4o による8軸・100点採点。
STEP 10 で全パイプラインデータ（財務・SWOT・真因・外部環境・内部環境）を統合して
各顧客/市場セグメントの戦略的優先度を定量評価する。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  スキーマ
# ------------------------------------------------------------------ #

class AxisScore(BaseModel):
    axis: str = ""
    score: int = 0           # 0–100
    weight: float = 1.0      # 相対ウェイト
    rationale: str = ""      # 採点根拠（具体的エビデンス）
    data_source: str = ""    # 参照データ（例: "財務サマリー 売上高成長率"）


class SegmentScore(BaseModel):
    segment_id: str = ""
    segment_name: str = ""
    description: str = ""
    total_score: float = 0.0         # 加重合計（0–100）
    priority_rank: int = 0           # 優先順位
    recommendation: str = ""        # "focus" | "maintain" | "selective" | "exit"
    strategic_rationale: str = ""   # 推奨根拠（2〜3文）
    axis_scores: List[AxisScore] = Field(default_factory=list)
    key_risks: List[str] = Field(default_factory=list)
    quick_wins: List[str] = Field(default_factory=list)


class SegmentEvaluation(BaseModel):
    segments: List[SegmentScore] = Field(default_factory=list)
    evaluation_summary: str = ""    # 全セグメント比較の総括（2〜3文）
    top_segment_id: str = ""
    scoring_methodology: str = ""   # 採点方法の注記
    confidence_score: float = 0.8


# ------------------------------------------------------------------ #
#  採点軸定義（8軸）
# ------------------------------------------------------------------ #

SCORING_AXES = [
    {"id": "market_size_growth",    "label": "市場規模・成長性",         "weight": 1.2},
    {"id": "competitive_fit",       "label": "自社競争力適合度",          "weight": 1.5},
    {"id": "profit_potential",      "label": "収益性ポテンシャル",        "weight": 1.5},
    {"id": "entry_feasibility",     "label": "参入障壁・実現可能性",      "weight": 1.0},
    {"id": "strategic_alignment",   "label": "戦略・ビジョン整合性",      "weight": 1.3},
    {"id": "risk_level",            "label": "リスク水準（逆転スコア）",  "weight": 1.0},
    {"id": "cac_efficiency",        "label": "顧客獲得コスト効率",        "weight": 0.8},
    {"id": "sustainability",        "label": "持続可能性・長期優位性",    "weight": 1.2},
]

_SYSTEM_PROMPT = """あなたはMcKinsey・BCGレベルの戦略コンサルタントです。
提供されたクライアントの全パイプラインデータを精査し、各セグメントを8軸で客観的に採点してください。

【絶対遵守ルール】
1. すべてのスコアはクライアントの実際のデータ（財務数値・SWOT・真因分析）に根拠を置くこと
2. 採点根拠（rationale）には必ず具体的なデータポイントまたは事実を引用すること
3. リスク水準軸は「高リスク＝低スコア」の逆転採点とすること
4. total_scoreは各軸スコアとウェイトの加重平均を正確に計算すること
5. セグメント間の相対評価を意識し、スコア差に意味を持たせること"""


def _build_prompt(input_data: Dict[str, Any]) -> str:
    def _dump(obj) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=2) if obj else "（データなし）"

    axes_desc = "\n".join(
        f'    - {ax["id"]}: "{ax["label"]}" (weight={ax["weight"]})'
        for ax in SCORING_AXES
    )
    axes_ids = [ax["id"] for ax in SCORING_AXES]

    # セグメント候補の抽出ヒント
    domain_hint = ""
    strategy = input_data.get("strategy_design") or {}
    domains = strategy.get("domain_strategies", [])
    if domains:
        names = [d.get("domain_name", "") for d in domains if d.get("domain_name")]
        if names:
            domain_hint = f"\n※ 既存の事業戦略ドメイン（参考）: {', '.join(names)}"

    return f"""以下の全パイプラインデータを基に、クライアントの顧客・市場セグメントを評価してください。{domain_hint}

## 会社情報
{_dump(input_data.get("company_info"))}

## 財務サマリー
{_dump(input_data.get("financial_summary"))}

## 外部環境分析
{_dump(input_data.get("external_env"))}

## SWOT分析
{_dump(input_data.get("swot"))}

## 内部環境調査結果
{_dump(input_data.get("internal_findings"))}

## 真因分析
{_dump(input_data.get("root_cause"))}

## ガードレール制約
{_dump(input_data.get("guardrails"))}

---
【採点軸（8軸・各0〜100点）】
{axes_desc}

各セグメントを上記8軸で採点し、以下のJSON形式で出力してください:

{{
  "segments": [
    {{
      "segment_id": "seg_1",
      "segment_name": "具体的なセグメント名（クライアントの業種・市場に固有）",
      "description": "セグメントの特徴説明（1〜2文）",
      "total_score": 加重平均スコア（0〜100の数値）,
      "priority_rank": 1,
      "recommendation": "focus または maintain または selective または exit",
      "strategic_rationale": "推奨根拠（財務データ・真因・SWOTを引用した2〜3文）",
      "axis_scores": [
        {{
          "axis": "{axes_ids[0]}",
          "score": 75,
          "weight": 1.2,
          "rationale": "根拠（具体的なデータポイントを引用）",
          "data_source": "参照データ名（例: 財務サマリー 売上高成長率）"
        }},
        {{"axis": "{axes_ids[1]}", "score": 0, "weight": 1.5, "rationale": "...", "data_source": "..."}},
        {{"axis": "{axes_ids[2]}", "score": 0, "weight": 1.5, "rationale": "...", "data_source": "..."}},
        {{"axis": "{axes_ids[3]}", "score": 0, "weight": 1.0, "rationale": "...", "data_source": "..."}},
        {{"axis": "{axes_ids[4]}", "score": 0, "weight": 1.3, "rationale": "...", "data_source": "..."}},
        {{"axis": "{axes_ids[5]}", "score": 0, "weight": 1.0, "rationale": "...", "data_source": "..."}},
        {{"axis": "{axes_ids[6]}", "score": 0, "weight": 0.8, "rationale": "...", "data_source": "..."}},
        {{"axis": "{axes_ids[7]}", "score": 0, "weight": 1.2, "rationale": "...", "data_source": "..."}}
      ],
      "key_risks": ["このセグメント固有のリスク×2〜3"],
      "quick_wins": ["即効性のある施策×2〜3"]
    }}
  ],
  "evaluation_summary": "全セグメント比較の総括（2〜3文、最優先セグメントと理由を含む）",
  "top_segment_id": "最優先セグメントのsegment_id",
  "scoring_methodology": "採点方法の注記（データソース・評価基準の簡潔な説明）",
  "confidence_score": 0.85
}}

【制約】
- セグメント数: 3〜5個（業種・規模・データ量に応じて判断）
- ガードレールの参入禁止市場はセグメントから除外すること
- total_scoreは必ず加重平均を正確に計算すること（(Σ score×weight) / Σ weight）
- priority_rankは total_score の降順で付番すること"""


def _parse_axis(raw: dict) -> AxisScore:
    score = raw.get("score", 0)
    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))
    weight = float(raw.get("weight", 1.0))
    return AxisScore(
        axis=raw.get("axis", ""),
        score=score,
        weight=weight,
        rationale=raw.get("rationale", ""),
        data_source=raw.get("data_source", ""),
    )


def _parse_segment(raw: dict, rank: int) -> SegmentScore:
    rec = raw.get("recommendation", "maintain")
    if rec not in ("focus", "maintain", "selective", "exit"):
        rec = "maintain"
    total = raw.get("total_score", 0)
    try:
        total = float(total)
    except (TypeError, ValueError):
        total = 0.0
    total = max(0.0, min(100.0, total))
    return SegmentScore(
        segment_id=raw.get("segment_id", f"seg_{rank}"),
        segment_name=raw.get("segment_name", ""),
        description=raw.get("description", ""),
        total_score=total,
        priority_rank=raw.get("priority_rank", rank),
        recommendation=rec,
        strategic_rationale=raw.get("strategic_rationale", ""),
        axis_scores=[_parse_axis(a) for a in raw.get("axis_scores", [])],
        key_risks=raw.get("key_risks", []),
        quick_wins=raw.get("quick_wins", []),
    )


def _parse_output(raw: dict) -> SegmentEvaluation:
    segments = []
    for i, seg_raw in enumerate(raw.get("segments", []), 1):
        segments.append(_parse_segment(seg_raw, i))
    # priority_rank を total_score 降順で再付番（LLM の計算ミス対策）
    segments.sort(key=lambda s: s.total_score, reverse=True)
    for i, seg in enumerate(segments, 1):
        seg.priority_rank = i
    top_id = segments[0].segment_id if segments else ""
    return SegmentEvaluation(
        segments=segments,
        evaluation_summary=raw.get("evaluation_summary", ""),
        top_segment_id=raw.get("top_segment_id", top_id),
        scoring_methodology=raw.get("scoring_methodology", ""),
        confidence_score=float(raw.get("confidence_score", 0.8)),
    )


def run_segment_scoring(input_data: Dict[str, Any]) -> SegmentEvaluation:
    """
    GPT-4o を呼び出してセグメント評価を実行する。
    input_data: 全パイプラインデータ（financial_summary, swot, root_cause, external_env,
                internal_findings, guardrails, company_info, strategy_design）
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
        temperature=0.2,
        max_tokens=3000,
    )

    if completion.usage:
        record_llm_usage(
            "segment_scoring",
            "gpt-4o",
            completion.usage.prompt_tokens,
            completion.usage.completion_tokens,
        )

    raw = json.loads(completion.choices[0].message.content)
    return _parse_output(raw)
