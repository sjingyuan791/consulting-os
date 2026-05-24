"""
OpenAI Agents SDK 統合レイヤー for Consulting OS.

既存パイプライン（core/pipeline/）・エージェント（core/agents/）・
品質ゲート（core/quality_gate_enhanced.py）は変更しない。
このパッケージは SDK 実行器として追加される最小侵襲レイヤー。

Public API:
    SDKRunner                 — 非同期実行ラッパー
    create_writer_agent()     — 章生成エージェント
    create_skeptic_agent()    — 品質監査エージェント
    create_cfo_agent()        — 財務分析エージェント（verified限定）
    create_strategy_agent()   — 戦略統合エージェント
"""
from core.agents_sdk.runner import SDKRunner
from core.agents_sdk.agents_definitions import (
    create_cfo_agent,
    create_skeptic_agent,
    create_strategy_agent,
    create_writer_agent,
)

__all__ = [
    "SDKRunner",
    "create_writer_agent",
    "create_skeptic_agent",
    "create_cfo_agent",
    "create_strategy_agent",
]
