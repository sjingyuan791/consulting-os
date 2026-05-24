"""
財務分析エンジン — 多年度財務データからAI財務診断を生成する。
GPT-4o, temperature=0.2, max_tokens=4000。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """あなたはMcKinsey・BCGレベルの財務専門コンサルタントです。
中小企業の多年度財務データを分析し、具体的な数値根拠に基づいた発見事項を生成してください。

【絶対遵守ルール】
1. 一般論を書かない。必ず具体的な数値（%、倍率、百万円）を根拠に含める
2. 発見事項は「原因→現状→影響」の構造で記述する
3. 内部環境分析（SWOT・組織・営業・オペレーション）への接続仮説を必ず書く
4. 財務的強みも必ず抽出する（弱みだけ書かない）
5. 優先度 high の発見事項を必ず3件以上含める
6. データ欠損・低信頼度の場合は「推定」と明示する"""


def _build_prompt(input_data: Dict[str, Any]) -> str:
    def _dump(obj) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=2) if obj else "（データなし）"

    company   = input_data.get("company_name", "")
    purpose   = input_data.get("purpose", "")
    stmts     = input_data.get("statements", {})
    loans     = input_data.get("loans", [])
    adjs      = input_data.get("adjustments", [])
    segs      = input_data.get("segments", [])
    bench     = input_data.get("benchmark", {})
    cf_notes  = input_data.get("cashflow_notes", {})

    # Build year-by-year ratio table
    ratio_text = ""
    for fy, data in sorted(stmts.items()):
        ratios = data.get("ratios", {})
        pl_r   = ratios.get("pl_ratios", {})
        bs_r   = ratios.get("bs_ratios", {})
        cf_r   = ratios.get("simple_cf", {})
        ccc_r  = ratios.get("ccc", {})
        roa_r  = ratios.get("roa_tree", {})
        norm_r = ratios.get("normalized", {})
        memos  = data.get("memos", [])
        tags   = [m.get("tag","") for m in memos if isinstance(m, dict) and m.get("tag")]

        ratio_text += f"""
### {fy}年度
- 売上高: {pl_r.get('revenue',0):.1f}M | 粗利率: {pl_r.get('gross_margin',0):.1f}% | 営業利益率: {pl_r.get('operating_margin',0):.1f}% | 経常利益率: {pl_r.get('ordinary_margin',0):.1f}%
- 自己資本比率: {bs_r.get('equity_ratio',0):.1f}% | 流動比率: {bs_r.get('current_ratio',0):.1f}% | 現預金月数: {bs_r.get('cash_months',0):.1f}ヶ月
- 簡易CF: {cf_r.get('simple_cf',0):.1f}M | CCC: {ccc_r.get('ccc',0):.1f}日 | ROA: {roa_r.get('roa',0):.2f}%
- 平年化補正後利益: {norm_r.get('normalized_profit', pl_r.get('ordinary_profit',0)):.1f}M
- 特記事項: {', '.join(tags) if tags else 'なし'}
"""

    # Loans summary
    total_principal = sum(float(ln.get("annual_principal", 0)) for ln in loans)
    total_balance   = sum(float(ln.get("balance", 0)) for ln in loans)
    loans_text = f"借入残高合計: {total_balance:.1f}M | 年間元金返済合計: {total_principal:.1f}M | 借入件数: {len(loans)}件"

    # Segments
    segs_text = ""
    for s in segs:
        segs_text += (f"- {s.get('segment_name','')}: 売上{float(s.get('sales_amount',0)):.1f}M "
                      f"粗利率{float(s.get('gross_margin',0)):.1f}% "
                      f"戦略={s.get('strategic_treatment','')}\n")

    # Benchmark
    bench_text = ""
    if bench:
        bench_text = (f"粗利率: {bench.get('gross_margin',0):.1f}% | "
                      f"営業利益率: {bench.get('operating_margin',0):.1f}% | "
                      f"ROA: {bench.get('roa',0):.2f}% | "
                      f"出所: {bench.get('source','不明')}")

    return f"""以下の財務データを分析し、JSON形式で財務診断を返してください。

## 対象企業
{company}（支援目的: {purpose}）

## 多年度財務指標
{ratio_text}

## 借入状況
{loans_text}

## 売上セグメント
{segs_text if segs_text else "（データなし）"}

## 業界ベンチマーク
{bench_text if bench_text else "（未入力）"}

## 資金繰りメモ
{_dump(cf_notes)}

---
以下のJSON形式で返してください:

{{
  "findings": [
    {{
      "finding": "具体的な発見事項（数値含む）",
      "evidence": "数値的根拠（年度・%・金額を明示）",
      "analysis_type": "profitability / cashflow / balance_sheet / growth / cost_structure / warning / segment",
      "priority": "high / medium / low",
      "recommendation": "コンサルタントへの提言（次のアクション）",
      "hypothesis_for_internal": "内部環境分析で検証すべき仮説"
    }}
  ],
  "summary": "財務分析の総括（3〜5文）",
  "key_issues": ["課題1", "課題2", "課題3"],
  "strengths": ["財務的強み1", "財務的強み2"]
}}

【分析タイプ別必須件数】
- profitability（収益性）: 最低2件
- cashflow（資金繰り）: 最低1件
- warning（要注意）: 優先度highで最低1件
- 財務的強み（strengths配列）: 最低2件"""


def _parse_output(raw: dict) -> dict:
    valid_types = {
        "profitability", "cashflow", "balance_sheet",
        "growth", "cost_structure", "warning", "segment",
    }
    findings = []
    for f in raw.get("findings", []):
        priority = f.get("priority", "medium")
        if priority not in ("high", "medium", "low"):
            priority = "medium"
        a_type = f.get("analysis_type", "profitability")
        if a_type not in valid_types:
            a_type = "profitability"
        findings.append({
            "finding":                f.get("finding", ""),
            "evidence":               f.get("evidence", ""),
            "analysis_type":          a_type,
            "priority":               priority,
            "recommendation":         f.get("recommendation", ""),
            "hypothesis_for_internal": f.get("hypothesis_for_internal", ""),
        })

    return {
        "findings":   findings,
        "summary":    raw.get("summary", ""),
        "key_issues": raw.get("key_issues", []),
        "strengths":  raw.get("strengths", []),
    }


def run_financial_analysis(input_data: Dict[str, Any]) -> dict:
    """
    多年度財務データからAI財務診断を生成する。
    戻り値: {findings, summary, key_issues, strengths}
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
            {"role": "user",   "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=4000,
    )

    if completion.usage:
        record_llm_usage(
            "financial_analysis",
            "gpt-4o",
            completion.usage.prompt_tokens,
            completion.usage.completion_tokens,
        )

    raw = json.loads(completion.choices[0].message.content)
    return _parse_output(raw)
