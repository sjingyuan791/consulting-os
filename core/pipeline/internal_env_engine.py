"""
内部環境分析エンジン — 外部/財務分析を踏まえた仮説検証ヒアリング質問を生成する。
GPT-4o, temperature=0.3, max_tokens=4000。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """あなたはMcKinsey・BCGレベルの戦略コンサルタントです。
外部環境分析と財務分析の具体的な発見事項を踏まえ、仮説検証型のヒアリング質問を設計してください。

【絶対遵守ルール】
1. 一般論の質問を出さない。外部/財務分析の具体的発見事項に必ず紐づけること
2. 何を検証する質問かを明示すること
3. 誰に聞くべきかを明示すること
4. 戦略仮説を反証する質問を必ず含めること
5. 不足データがある場合は資料依頼として出すこと
6. 質問数は15〜25問。多すぎず、少なすぎず
7. 優先度 high の質問を必ず5問以上含めること"""


def _build_prompt(input_data: Dict[str, Any]) -> str:
    def _dump(obj) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=2) if obj else "（データなし）"

    company_info      = input_data.get("company_info", {})
    external_analysis = input_data.get("external_analysis", {})
    financial_summary = input_data.get("financial_summary", {})
    hypotheses        = input_data.get("strategy_hypotheses", "")
    purpose           = input_data.get("purpose", "")

    return f"""以下の分析結果を踏まえて、内部環境分析のための仮説検証ヒアリング質問を生成してください。

## 会社情報
{_dump(company_info)}

## 支援目的
{purpose}

## 戦略仮説（コンサルタント設定）
{hypotheses if hypotheses else "（未設定）"}

## 外部環境分析の発見事項
{_dump(external_analysis)}

## 財務分析の発見事項
{_dump(financial_summary)}

---
以下のカテゴリで質問を生成し、JSONで返してください:

{{
  "questions": [
    {{
      "question": "具体的な質問文（外部/財務分析の発見に紐づく）",
      "purpose": "何を検証するための質問か（1文）",
      "question_category": "opportunity_fit / threat_resilience / financial_cause / sales_structure / strength_to_profit_cashflow / execution_capacity / falsification / document_request",
      "linked_analysis": "external / financial / both",
      "linked_finding": "紐づく外部/財務分析の発見事項（具体的に）",
      "hypothesis_to_test": "検証する仮説",
      "priority": "high / medium / low",
      "target_person": "経営者 / 後継者 / 経理担当 / 営業担当 / 現場責任者 / 外部専門家",
      "expected_evidence": "回答・確認に使える資料・データ",
      "follow_up_if_yes": "YESの場合の次の確認",
      "follow_up_if_no": "NOの場合の次の確認",
      "required_data": "追加で必要なデータ",
      "domain": "organization / capability / marketing / product / operation / cost_mgmt / it / customer_asset",
      "adoption_status": "pending"
    }}
  ],
  "missing_inputs": [
    {{
      "data_name": "不足データ名",
      "reason": "なぜ必要か",
      "priority": "high / medium / low",
      "collection_method": "hearing / document_request / sales_data_processing / site_visit / system_export",
      "impact_on_analysis": "分析への影響"
    }}
  ],
  "analysis_summary": "外部/財務分析から見えた内部環境分析の焦点（2〜3文）"
}}

【カテゴリ別の必須質問数】
- opportunity_fit（外部機会を取れるか）: 最低3問
- financial_cause（財務課題の原因）: 最低3問
- strength_to_profit_cashflow（強みが利益/CFに転換されているか）: 最低2問
- falsification（仮説の反証）: 最低2問
- document_request（資料依頼）: 最低2問"""


def _parse_output(raw: dict) -> dict:
    questions = []
    for q in raw.get("questions", []):
        priority = q.get("priority", "medium")
        if priority not in ("high", "medium", "low"):
            priority = "medium"
        cat = q.get("question_category", "opportunity_fit")
        valid_cats = {
            "opportunity_fit", "threat_resilience", "financial_cause",
            "sales_structure", "strength_to_profit_cashflow",
            "execution_capacity", "falsification", "document_request",
        }
        if cat not in valid_cats:
            cat = "opportunity_fit"
        domain = q.get("domain", "organization")
        valid_domains = {
            "organization", "capability", "marketing", "product",
            "operation", "cost_mgmt", "it", "customer_asset",
        }
        if domain not in valid_domains:
            domain = "organization"
        questions.append({
            "question":        q.get("question", ""),
            "purpose":         q.get("purpose", ""),
            "question_category": cat,
            "linked_analysis": q.get("linked_analysis", "both"),
            "linked_finding":  q.get("linked_finding", ""),
            "hypothesis_to_test": q.get("hypothesis_to_test", ""),
            "priority":        priority,
            "target_person":   q.get("target_person", "経営者"),
            "expected_evidence": q.get("expected_evidence", ""),
            "follow_up_if_yes": q.get("follow_up_if_yes", ""),
            "follow_up_if_no":  q.get("follow_up_if_no", ""),
            "required_data":   q.get("required_data", ""),
            "domain":          domain,
            "adoption_status": "pending",
        })

    missing = []
    for m in raw.get("missing_inputs", []):
        priority = m.get("priority", "medium")
        if priority not in ("high", "medium", "low"):
            priority = "medium"
        missing.append({
            "data_name":   m.get("data_name", ""),
            "reason":      m.get("reason", ""),
            "priority":    priority,
            "collection_method": m.get("collection_method", "hearing"),
            "impact_on_analysis": m.get("impact_on_analysis", ""),
        })

    return {
        "questions":       questions,
        "missing_inputs":  missing,
        "analysis_summary": raw.get("analysis_summary", ""),
    }


def generate_interview_questions(input_data: Dict[str, Any]) -> dict:
    """
    外部環境/財務分析を踏まえた仮説検証ヒアリング質問を生成する。
    input_data: {company_info, external_analysis, financial_summary,
                 strategy_hypotheses, purpose}
    戻り値: {questions: [...], missing_inputs: [...], analysis_summary: ""}
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
        max_tokens=4000,
    )

    if completion.usage:
        record_llm_usage(
            "internal_interview_questions",
            "gpt-4o",
            completion.usage.prompt_tokens,
            completion.usage.completion_tokens,
        )

    raw = json.loads(completion.choices[0].message.content)
    return _parse_output(raw)
