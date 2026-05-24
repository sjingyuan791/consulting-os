"""
Chat Engine - OpenAI ストリーミング応答 + プロジェクトコンテキスト注入
"""
from __future__ import annotations

import logging
from typing import Generator

from openai import OpenAI

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  System Prompt
# ------------------------------------------------------------------ #

_SYSTEM_PROMPT = """あなたは「Consulting OS」専属のシニア経営コンサルタントAIです。
プロジェクトの全分析データ（財務・外部環境・内部能力・理念・SWOT・真因・戦略仮説）を踏まえ、
コンサルタントの実務パートナーとして機能します。

【行動原則】
- 登録済みの分析データは必ず参照し、「データが示すこと」を具体的に言及する
- データがない項目については「〇〇のデータが未登録です。登録すると精度が上がります」と明示する
- 仮説は仮説として断言せず「〜と考えられます」「〜の可能性が高いです」と記述する
- 結論→根拠→アクションの順で回答を構造化する
- 数値は具体的に、定性情報は構造化して回答する

【対応範囲】
- 財務分析・KPI解説（ROA/ROE/営業利益率/資金繰り）
- 外部環境分析（PEST・5F・市場トレンド）
- SWOT分析の深掘り・クロスSWOT
- 真因分析・ロジックツリー
- 戦略仮説の検証・精緻化
- ドメイン設定・ポジショニング戦略
- 機能別戦略・戦術の具体化
- 中期数値計画（売上・CF・3か年PL）
- 実行計画・KPI設計

【ナビゲーション案内】
特定機能が必要な場合のページ名のみ記載：
データ入力 → 「データ入力ページ（STEP1-3）」
財務分析 → 「財務・事業分析ページ（STEP4）」
SWOT → 「SWOT分析ページ（STEP8）」
中期計画 → 「中期経営計画ページ（STEP15）」
"""


# ------------------------------------------------------------------ #
#  Context
# ------------------------------------------------------------------ #

def get_client_context(client_id: str | None) -> str:
    """
    ProjectContextを使ってリッチなコンテキスト文字列を返す。
    全ステップの分析結果を統合してAIに渡す。
    """
    if not client_id:
        return ""
    try:
        from core.project_context import ProjectContext
        ctx = ProjectContext.load(client_id)
        return ctx.to_prompt_text(scope="full")
    except Exception as e:
        logger.warning("get_client_context failed, falling back: %s", e)
        # フォールバック: 基本情報のみ
        try:
            from core.supabase_client import get_supabase_client
            sb = get_supabase_client()
            res = sb.table("clients").select("name, industry, location").eq("id", client_id).single().execute()
            if res.data:
                c = res.data
                return (
                    f"\n\n【クライアント】{c.get('name','')}"
                    f"（{c.get('industry','')}、{c.get('location','')}）"
                )
        except Exception:
            pass
        return ""


# ------------------------------------------------------------------ #
#  Streaming Chat
# ------------------------------------------------------------------ #

def stream_chat_response(
    messages: list[dict],
    client_context: str = "",
) -> Generator:
    """
    GPT-4o でストリーミング応答を返す。
    client_context には get_client_context() の結果を渡す。
    """
    oai = OpenAI()

    system_content = _SYSTEM_PROMPT
    if client_context:
        system_content += client_context

    full_messages = [{"role": "system", "content": system_content}] + messages

    return oai.chat.completions.create(
        model="gpt-4o",
        messages=full_messages,
        stream=True,
        temperature=0.7,
        max_tokens=2048,
    )
