"""
Output type schemas for SDK Agents.
Each agent returns a typed Pydantic model as its final output.

不変条件:
- missing_inputs は必ず返す（推測しない）
- AI は暫定仮説・代替仮説・反証条件・不足データ・即実行打ち手を返す
- 結論ではなく仮説形式
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class WriterAgentOutput(BaseModel):
    """Writer Agent の出力。中期経営計画の1章分。"""
    section_id: int
    narrative: str                          # コンサルレポート文体の本文
    data: Dict[str, Any]                    # 章の構造化データ（スキーマ準拠）
    missing_inputs: List[str] = []          # 不足データ一覧（推測しない）
    assumptions: List[str] = []            # 分析前提
    alternative_hypotheses: List[str] = [] # 代替仮説
    counter_evidence_conditions: List[str] = []  # 反証条件
    immediate_actions: List[str] = []      # 即実行打ち手


class SkepticAgentOutput(BaseModel):
    """Skeptic Agent の出力。Decision-Grade 検証結果。"""
    status: Literal["approved", "warning", "blocked"]
    blocking_reasons: List[str] = []       # ブロック理由（blockedの場合）
    warnings: List[str] = []              # 警告（warning/approved）
    missing_evidence: List[str] = []      # エビデンス未提示の主張
    numerical_inconsistencies: List[str] = []  # 数値不整合
    checkpoint_id: Optional[str] = None  # blocked→human_checkpoints.id


class CFOAgentOutput(BaseModel):
    """CFO Agent の出力。financials_verified=False なら analysis は None。"""
    financials_verified: bool
    analysis: Optional[Dict[str, Any]] = None
    missing_inputs: List[str] = []         # verified=False なら ["financials_verified"]
    reconciliation_result: Optional[Dict[str, Any]] = None  # BS・粗利整合チェック結果


class StrategyAgentOutput(BaseModel):
    """Strategy Agent の出力。暫定仮説・代替仮説・反証条件・即実行打ち手。"""
    provisional_hypothesis: str            # 暫定仮説（断言しない）
    alternative_hypotheses: List[str] = [] # 代替仮説
    counter_evidence_conditions: List[str] = []  # 反証条件
    missing_inputs: List[str] = []        # 不足データ
    immediate_actions: List[str] = []     # 即実行打ち手
    strategy_draft: Optional[Dict[str, Any]] = None  # 戦略骨格ドラフト
