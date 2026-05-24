from typing import Dict, Any, List, Optional
import json
import logging
from core.agents.base import BaseAgent, AgentResult
from core.schemas.midterm_plan_schema import (
    FinancialNumericalPlan, ExternalEnvironment, InternalEnvironment,
    RootCauseAnalysis, PESTItem, CompetitorProfile, ResourceAssessment,
    YearlyFinancials
)

logger = logging.getLogger(__name__)

class FinancialAnalyst(BaseAgent):
    """財務分析エージェント (CFO Proxy)"""

    async def run(self, context: Dict[str, Any]) -> AgentResult:
        financial_data = context.get("financial_data", {})
        
        system_prompt = """あなたは熟練のCFO（最高財務責任者）です。
提供された財務データ（PL/BS/CF）に基づき、企業の財務状態を厳しく、かつ客観的に分析してください。
以下の観点で分析を行い、JSON形式で出力してください。

1. 収益性（Profitability）
2. 安全性（Stability）
3. 成長性（Growth）
4. 将来予測（Projection）: 過去のトレンドから、成長率を保守的・現実的・楽観的の3シナリオで検討せよ。

出力は具体的な数値を用いること。「良い」「悪い」だけでなく、なぜそう言えるのかをデータで語れ。"""

        user_prompt = f"""以下の財務データを分析してください:
{json.dumps(financial_data, ensure_ascii=False, indent=2)}"""

        # TODO: Define a specific Output Schema for Financial Analyst if needed
        # For now, return text analysis + structured KPI projection
        narrative = await self._call_llm(system_prompt, user_prompt)
        
        # 簡易的にKPIデータを抽出するロジック（実際はStructured Outputを使うべき）
        # ここではNarrativeを返す
        return AgentResult(narrative=narrative, data={"source": "financial_data"})

class MarketResearcher(BaseAgent):
    """市場調査エージェント (CMO Proxy)"""
    
    async def run(self, context: Dict[str, Any]) -> AgentResult:
        external_data = context.get("external_data", {})
        client_industry = context.get("industry", "Unknown")
        
        # RAG Search
        rag_query = f"{client_industry} 市場動向 競合 機会 脅威 トレンド"
        rag_context = self._get_rag_context(rag_query)
        
        system_prompt = """あなたは鋭敏なマーケティングリサーチャーです。
提供された外部データとRAG検索結果に基づき、市場環境を分析してください。
あやふやな予測ではなく、ファクト（事実）に基づいたPEST分析と3C分析を行ってください。"""

        user_prompt = f"""
業界: {client_industry}
外部データ: {json.dumps(external_data, ensure_ascii=False)}
調査レポート(RAG): {rag_context}

分析項目:
1. マクロ環境(PEST)の決定的な変化
2. 競合の動きと自社の立ち位置
3. "Blue Ocean"（未開拓の機会）の特定
"""
        narrative = await self._call_llm(system_prompt, user_prompt)
        return AgentResult(narrative=narrative, data={"rag_context_used": bool(rag_context)})

class InternalAuditor(BaseAgent):
    """内部監査エージェント (CHRO/COO Proxy)"""
    
    async def run(self, context: Dict[str, Any]) -> AgentResult:
        internal_data = context.get("internal_data", {})
        
        system_prompt = """あなたは厳格な内部監査人兼人事責任者です。
組織の内部リソース（ヒト・モノ・カネ・情報）をVRIOフレームワークを用いて評価してください。
「強み」と「弱み」を忖度なくリストアップし、真の競争優位性の源泉（Core Competence）を特定してください。"""
        
        user_prompt = f"""内部データ: {json.dumps(internal_data, ensure_ascii=False)}"""
        
        narrative = await self._call_llm(system_prompt, user_prompt)
        return AgentResult(narrative=narrative, data={})
