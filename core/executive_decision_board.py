"""
Executive decision board heuristics for Consulting OS.

This module turns pipeline progress into a management-facing view:
readiness to decide, unresolved questions, and the next best action.
It is intentionally deterministic so the UI can challenge LLM output
instead of merely displaying it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


TOTAL_STEPS = 18


@dataclass(frozen=True)
class DecisionBoard:
    readiness_score: int
    status: str
    status_tone: str
    next_decision: str
    next_action: str
    executive_summary: str
    blocking_questions: list[str]
    quality_gates: list[str]
    differentiation_signals: list[str]
    completed_steps: int
    total_steps: int = TOTAL_STEPS


def parse_pipeline_steps(project_or_notes: dict[str, Any] | str | None) -> dict[str, str]:
    """Extract pipeline step statuses from a project row or notes JSON."""
    if not project_or_notes:
        return {}

    if isinstance(project_or_notes, str):
        raw_notes = project_or_notes
    else:
        raw_notes = project_or_notes.get("notes") or "{}"

    try:
        notes = json.loads(raw_notes)
    except (TypeError, json.JSONDecodeError):
        return {}

    steps = notes.get("pipeline_steps", {})
    if not isinstance(steps, dict):
        return {}
    return {str(k): str(v) for k, v in steps.items()}


def build_decision_board(
    pipeline_steps: dict[str, str] | None,
    *,
    total_steps: int = TOTAL_STEPS,
) -> DecisionBoard:
    steps = pipeline_steps or {}
    done = {int(k) for k, v in steps.items() if str(v) == "done" and str(k).isdigit()}
    in_progress = {int(k) for k, v in steps.items() if str(v) == "in_progress" and str(k).isdigit()}

    foundation_done = len(done & {1, 2, 3, 4, 5, 6})
    strategy_done = len(done & {7, 8, 9, 10, 11, 12, 13, 14})
    numbers_done = len(done & {15, 16, 17})
    execution_done = 18 in done

    score = 0
    score += round((foundation_done / 6) * 35)
    score += round((strategy_done / 8) * 25)
    score += round((numbers_done / 3) * 30)
    score += 10 if execution_done else 0
    score = min(100, max(0, score))

    status, tone = _status_for_score(score, foundation_done, strategy_done, numbers_done, execution_done)
    next_decision, next_action = _next_move(done, in_progress)
    blocking_questions = _blocking_questions(foundation_done, strategy_done, numbers_done, execution_done)
    quality_gates = _quality_gates(foundation_done, strategy_done, numbers_done, execution_done)
    differentiation = [
        "LLMの文章ではなく、データ収集・戦略・数値計画・実行計画を分けて決裁前の不足を明示",
        "財務シミュレーション、品質ゲート、承認ログにより、なぜその判断に至ったかを追跡可能",
        "18ステップの進捗を社長向けの論点、未解決リスク、次アクションへ変換",
    ]

    summary = _summary(status, score, next_decision)
    return DecisionBoard(
        readiness_score=score,
        status=status,
        status_tone=tone,
        next_decision=next_decision,
        next_action=next_action,
        executive_summary=summary,
        blocking_questions=blocking_questions,
        quality_gates=quality_gates,
        differentiation_signals=differentiation,
        completed_steps=len(done),
        total_steps=total_steps,
    )


def board_from_project(project: dict[str, Any]) -> DecisionBoard:
    return build_decision_board(parse_pipeline_steps(project))


def _status_for_score(
    score: int,
    foundation_done: int,
    strategy_done: int,
    numbers_done: int,
    execution_done: bool,
) -> tuple[str, str]:
    if foundation_done < 3:
        return "データ不足", "danger"
    if strategy_done < 4:
        return "論点形成中", "warning"
    if numbers_done < 2:
        return "数値検証待ち", "warning"
    if score >= 90 and execution_done:
        return "実行判断可能", "success"
    if score >= 70:
        return "決裁前レビュー", "success"
    return "検証継続", "warning"


def _next_move(done: set[int], in_progress: set[int]) -> tuple[str, str]:
    if 1 not in done:
        return "決算書と月次データを揃える", "決算書アップロードを完了し、PL/BS/CFの最低限の根拠を確定する"
    if 2 not in done:
        return "市場と競合の前提を置く", "外部環境調査で市場成長、競争圧力、規制リスクを登録する"
    if 4 not in done:
        return "収益構造を読む", "財務・事業分析でROA、利益率、資金繰りの制約を確認する"
    if 8 not in done or 9 not in done:
        return "勝ち筋と真因を一つに絞る", "SWOTと真因分析をつなげ、社長が捨てる選択肢まで明示する"
    if 10 not in done or 11 not in done:
        return "どこで勝つかを決める", "全社戦略仮説と事業ドメインを比較し、選ばない領域を記録する"
    if 15 not in done or 16 not in done or 17 not in done:
        return "戦略をPL/CFで検証する", "売上計画、CF計画、3か年数値計画を生成し、DSCRと資金ショートを確認する"
    if 18 not in done:
        return "実行責任を確定する", "KPI、責任者、期限、レビュー頻度を決め、実行管理へ接続する"
    if in_progress:
        return "進行中タスクの決着", "進行中のステップを完了または差し戻し、決裁ログを残す"
    return "実行判断", "社長決裁として採用、保留、撤退条件付き採用のいずれかを記録する"


def _blocking_questions(
    foundation_done: int,
    strategy_done: int,
    numbers_done: int,
    execution_done: bool,
) -> list[str]:
    questions: list[str] = []
    if foundation_done < 6:
        questions.append("判断の根拠になる財務・外部環境・内部環境データは揃っているか")
    if strategy_done < 8:
        questions.append("成長領域、撤退・非注力領域、勝ち筋の因果関係は説明できるか")
    if numbers_done < 3:
        questions.append("売上計画とキャッシュフローは、悲観シナリオでも資金ショートしないか")
    if not execution_done:
        questions.append("誰が、いつまでに、どのKPIで進捗を判断するか決まっているか")
    if not questions:
        questions.append("撤退条件と見直しタイミングを社長決裁メモに残したか")
    return questions


def _quality_gates(
    foundation_done: int,
    strategy_done: int,
    numbers_done: int,
    execution_done: bool,
) -> list[str]:
    gates: list[str] = []
    gates.append("財務データの欠損・異常値チェック")
    if foundation_done >= 4:
        gates.append("外部環境と内部課題の整合チェック")
    if strategy_done >= 4:
        gates.append("戦略仮説とSWOT/真因の因果チェック")
    if numbers_done >= 2:
        gates.append("PL/CF/借入返済能力のシナリオチェック")
    if execution_done:
        gates.append("KPI、責任者、期限、レビュー頻度の実行可能性チェック")
    return gates


def _summary(status: str, score: int, next_decision: str) -> str:
    if score < 40:
        return f"{status}です。現時点では社長決裁よりも、まず「{next_decision}」が必要です。"
    if score < 70:
        return f"{status}です。方向性は見え始めていますが、決裁には「{next_decision}」が残っています。"
    if score < 90:
        return f"{status}です。社長決裁に近い状態ですが、最後に「{next_decision}」を確認してください。"
    return f"{status}です。採用・保留・条件付き採用を記録できる状態です。"
