"""
Stage 2: Root Cause Inductive Engine — GPT-4o driven, client-specific.
Constructs causal maps and identifies root causes from actual client data.
No hardcoded causal templates.
"""
from typing import Dict, Any, Optional, List
from core.pipeline.base_engine import AIEngine, EngineConfig
from core.schemas.pipeline_stages import (
    Stage2Output, CausalMap, CausalNode, CausalEdge,
    RootCause, CausalChain,
)
import json
import logging

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """あなたはMcKinsey・BCGレベルの戦略コンサルタントです。
クライアント固有の財務データ・SWOT・内部環境調査・外部環境情報を分析し、
構造的な根本原因を特定してください。

【絶対遵守ルール】
1. 「競争激化」「需要低下」等の汎用原因は使用禁止。クライアント固有の数値・事実に基づくこと
2. 主要根本原因は1つに絞り、財務数値との因果連鎖を明示すること
3. supporting_evidenceは財務数値・調査結果の具体的な数値・事実であること
4. 対処可能性（addressability）はクライアントの経営資源・組織能力を考慮すること"""


def _safe_float(v, default=0.5) -> float:
    try:
        f = float(v)
        return max(0.0, min(1.0, f))
    except (TypeError, ValueError):
        return default


def _parse_node(d: dict) -> CausalNode:
    nt = d.get("node_type", "intermediate")
    if nt not in ("symptom", "intermediate", "root_cause", "external"):
        nt = "intermediate"
    return CausalNode(
        id=str(d.get("id", "node")),
        label=str(d.get("label", ""))[:60],
        node_type=nt,
        category=d.get("category"),
        description=d.get("description"),
    )


def _parse_edge(d: dict) -> CausalEdge:
    rel = d.get("relationship", "causes")
    if rel not in ("causes", "amplifies", "inhibits", "correlates"):
        rel = "causes"
    return CausalEdge(
        source=str(d.get("source", "")),
        target=str(d.get("target", "")),
        relationship=rel,
        strength=_safe_float(d.get("strength", 0.7)),
        evidence=str(d.get("evidence", "")),
    )


def _parse_root_cause(d: dict, rank: int) -> RootCause:
    addr = d.get("addressability", "medium")
    if addr not in ("high", "medium", "low"):
        addr = "medium"
    return RootCause(
        id=str(d.get("id", f"cause_{rank}")),
        description=str(d.get("description", "")),
        category=str(d.get("category", "operational")),
        confidence=_safe_float(d.get("confidence", 0.7)),
        supporting_evidence=d.get("supporting_evidence", []),
        impact_scope=d.get("impact_scope", []),
        addressability=addr,
        priority_rank=rank,
    )


def _parse_output(raw: dict) -> Stage2Output:
    nodes = [_parse_node(n) for n in raw.get("causal_nodes", [])]
    edges = [_parse_edge(e) for e in raw.get("causal_edges", [])]

    # Validate edge references
    node_ids = {n.id for n in nodes}
    edges = [e for e in edges if e.source in node_ids and e.target in node_ids]

    causal_map = CausalMap(nodes=nodes, edges=edges)

    primary_raw = raw.get("primary_root_cause", {})
    primary = _parse_root_cause(primary_raw, 1)

    secondary = [
        _parse_root_cause(d, i + 2)
        for i, d in enumerate(raw.get("secondary_causes", [])[:3])
    ]

    chains = []
    for i, c in enumerate(raw.get("causal_chains", [])[:5]):
        chains.append(CausalChain(
            chain_id=str(c.get("chain_id", f"chain_{i+1}")),
            nodes=[str(n) for n in c.get("nodes", [])],
            total_strength=_safe_float(c.get("total_strength", 0.7)),
            description=str(c.get("description", "")),
        ))

    return Stage2Output(
        causal_map=causal_map,
        primary_root_cause=primary,
        secondary_causes=secondary,
        causal_chains=chains,
        feedback_loops=[],
        leverage_points=raw.get("leverage_points", []),
        confidence_score=_safe_float(raw.get("confidence_score", 0.75)),
        analysis_summary=str(raw.get("analysis_summary", "")),
    )


class RootCauseEngine(AIEngine[Dict[str, Any], Stage2Output]):
    """GPT-4o driven root cause analysis. Requires client-specific context in input_data."""

    STAGE_NUMBER = 2
    STAGE_NAME = "Root Cause Inductive Engine"

    async def process(
        self,
        input_data: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Stage2Output:
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
            temperature=0.2,
            max_tokens=4096,
        )

        if completion.usage:
            record_llm_usage(
                "root_cause_analysis",
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

        return f"""以下のクライアント固有データを基に、構造的な根本原因を特定してください。

## 会社情報
{_dump(input_data.get("company_info"))}

## 財務分析結果（STEP 4）
{_dump(input_data.get("financial_analysis"))}

## SWOT分析（STEP 8）
{_dump(input_data.get("swot"))}

## 内部環境調査結果（STEP 5-6）
{_dump(input_data.get("internal_findings"))}

## 外部環境（STEP 2）
{_dump(input_data.get("external_env"))}

## ビジョン・ミッション（STEP 7）
{_dump(input_data.get("vision_mission"))}

---
以下のJSON形式で回答してください。すべての分析はクライアント固有のデータに基づくこと。

{{
  "causal_nodes": [
    {{
      "id": "symptom_低利益率",
      "label": "営業利益率X%（業界平均Y%を下回る）",
      "node_type": "symptom",
      "category": "financial",
      "description": "財務データから観測された症状（具体的数値を含む）"
    }},
    {{
      "id": "intermediate_原価高騰",
      "label": "原材料費の上昇",
      "node_type": "intermediate",
      "category": "operational",
      "description": "症状と根本原因を結ぶ中間要因"
    }},
    {{
      "id": "root_仕入構造",
      "label": "単一サプライヤー依存による価格交渉力の欠如",
      "node_type": "root_cause",
      "category": "operational",
      "description": "クライアント固有の根本構造的問題"
    }}
  ],
  "causal_edges": [
    {{
      "source": "root_仕入構造",
      "target": "intermediate_原価高騰",
      "relationship": "causes",
      "strength": 0.85,
      "evidence": "仕入先上位3社で仕入総額の78%を占める（内部調査）"
    }},
    {{
      "source": "intermediate_原価高騰",
      "target": "symptom_低利益率",
      "relationship": "causes",
      "strength": 0.9,
      "evidence": "原価率が過去3年でX%→Y%に悪化（財務データ）"
    }}
  ],
  "primary_root_cause": {{
    "id": "root_仕入構造",
    "description": "クライアント固有の根本原因の詳細説明（汎用表現禁止・数値含む）",
    "category": "operational",
    "confidence": 0.82,
    "supporting_evidence": [
      "具体的な財務数値や調査結果に基づくエビデンス1",
      "具体的なエビデンス2"
    ],
    "impact_scope": ["営業利益率", "キャッシュフロー", "競争力"],
    "addressability": "high"
  }},
  "secondary_causes": [
    {{
      "id": "cause_2",
      "description": "副次的原因（クライアント固有）",
      "category": "market",
      "confidence": 0.65,
      "supporting_evidence": ["エビデンス"],
      "impact_scope": ["影響する指標"],
      "addressability": "medium"
    }}
  ],
  "causal_chains": [
    {{
      "chain_id": "chain_1",
      "nodes": ["root_仕入構造", "intermediate_原価高騰", "symptom_低利益率"],
      "total_strength": 0.76,
      "description": "根本原因→中間要因→症状の因果連鎖説明"
    }}
  ],
  "leverage_points": [
    "最も高い介入効果が期待できるポイント（具体的）",
    "次のレバレッジポイント"
  ],
  "analysis_summary": "財務データ・SWOT・内部調査から導出した根本原因の論拠説明（200字以上）",
  "confidence_score": 0.78
}}

【制約】
- causal_nodesのnode_typeは symptom/intermediate/root_cause/external のいずれか
- causal_edgesのrelationshipは causes/amplifies/inhibits/correlates のいずれか
- edgeのsource/targetは必ずcausal_nodesのidと一致すること
- primary_root_causeのidはcausal_nodesのいずれかのidと一致すること
- supporting_evidenceは「財務データのX%」「調査項目のYに関する知見」等の具体的事実のみ"""


def create_root_cause_engine(config: Optional[EngineConfig] = None) -> RootCauseEngine:
    return RootCauseEngine(config)
