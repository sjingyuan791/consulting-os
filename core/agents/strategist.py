from typing import Dict, Any, List, Optional
import json
import logging
from core.agents.base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

class StrategyDirector(BaseAgent):
    """戦略ディレクターエージェント (CEO Proxy)"""
    
    async def run(self, context: Dict[str, Any]) -> AgentResult:
        financial_report = context.get("financial_report", "")
        market_report = context.get("market_report", "")
        internal_report = context.get("internal_report", "")
        
        system_prompt = """あなたは経験豊富な戦略ディレクター（CEO）です。
財務、市場、内部組織の3つの視点からの分析レポートを統合し、最適な戦略方針を策定してください。
矛盾する情報がある場合は、トレードオフを考慮して意思決定を行ってください。

以下の要素を含む戦略案を作成してください：
1. 戦略的意図（Strategic Intent）: 3年後のありたい姿。
2. 成長の方向性: アンゾフマトリクスに基づく成長エンジン。
3. 重点施策: リソースを集中投下すべき3つの領域。
4. クロスSWOT分析に基づく具体的な戦略オプション（SO/WO/ST/WT）。"""
        
        user_prompt = f"""
=== 財務分析レポート ===
{financial_report}

=== 市場調査レポート ===
{market_report}

=== 内部監査レポート ===
{internal_report}

これらを統合し、勝てる戦略を立案せよ。
"""
        
        narrative = await self._call_llm(system_prompt, user_prompt)
        return AgentResult(narrative=narrative, data={})

class DevilsAdvocate(BaseAgent):
    """悪魔の代弁者エージェント (Critic / Quality Assurance)"""
    
    async def run(self, context: Dict[str, Any]) -> AgentResult:
        draft_strategy = context.get("draft_strategy", "")
        financial_constraints = context.get("financial_constraints", "")
        
        system_prompt = """あなたは憎まれ役を買って出る「悪魔の代弁者（Devil's Advocate）」です。
提案された戦略案に対し、徹底的に批判的なレビューを行ってください。
「楽観的すぎる予測」「論理の飛躍」「リソース不足の無視」などを厳しく指摘し、リスクを顕在化させてください。

ただし、単なる否定ではなく、戦略をより強固にするための「建設的な批判」を行ってください。
指摘事項と、それに対する修正案を提示すること。"""
        
        user_prompt = f"""
=== 提案された戦略案 ===
{draft_strategy}

=== 財務的制約 ===
{financial_constraints}

この戦略の穴を見つけ出し、修正案を提示せよ。
"""
        
        narrative = await self._call_llm(system_prompt, user_prompt)
        return AgentResult(narrative=narrative, data={"criticism_applied": True})
