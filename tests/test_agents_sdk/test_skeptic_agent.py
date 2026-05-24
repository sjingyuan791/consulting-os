"""
Skeptic Agent テスト:
- missing_inputs がある RefinedStrategicPlan が Decision-Grade でブロックされる
- run_quality_gate ツールのラッパーが正しく status/blocking_reasons を返す
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from tests.test_agents_sdk.conftest import call_tool


# ============================================================
# check_strategic_refinement_quality 直接テスト（モックプラン）
# ============================================================

def test_quality_gate_blocks_missing_inputs():
    """
    missing_inputs を持つプランは check_strategic_refinement_quality が
    status='blocked' を返すことを検証する。
    plan 引数は Any 型なので MagicMock で代替できる。
    """
    from core.quality_gate_enhanced import check_strategic_refinement_quality
    from core.schemas.refinement_schema import MissingInput

    plan = MagicMock()
    plan.financials_verified = False
    plan.forecast_source = "assumption_only"
    plan.missing_inputs = [
        MissingInput(
            field_name="revenue_projection",
            reason="Revenue forecast not provided",
            impact="Plan cannot be evaluated without revenue data",
        )
    ]
    plan.scenarios = []
    plan.external_constraints = None
    plan.confidence_level = 0.5

    result = check_strategic_refinement_quality(plan)

    assert result.status == "blocked"
    assert len(result.blocking_reasons) > 0
    # missing_inputs のフィールド名がブロック理由に含まれる
    assert any("revenue_projection" in reason for reason in result.blocking_reasons)


def test_quality_gate_blocks_unverified_financials():
    """financials_verified=False はそれ単体でブロック理由になる。"""
    from core.quality_gate_enhanced import check_strategic_refinement_quality

    plan = MagicMock()
    plan.financials_verified = False
    plan.forecast_source = "deterministic_engine"
    plan.missing_inputs = []
    plan.scenarios = []
    plan.external_constraints = None
    plan.confidence_level = 0.8

    result = check_strategic_refinement_quality(plan)

    assert result.status == "blocked"
    assert any("Financials" in r or "財務" in r for r in result.blocking_reasons)


def test_quality_gate_blocks_wrong_forecast_source():
    """forecast_source が 'deterministic_engine' 以外はブロックされる。"""
    from core.quality_gate_enhanced import check_strategic_refinement_quality

    plan = MagicMock()
    plan.financials_verified = True
    plan.forecast_source = "assumption_only"
    plan.missing_inputs = []
    plan.scenarios = []
    plan.external_constraints = None
    plan.confidence_level = 0.8

    result = check_strategic_refinement_quality(plan)

    assert result.status == "blocked"
    assert any("forecast" in r.lower() or "予測" in r for r in result.blocking_reasons)


# ============================================================
# run_quality_gate ツールのラッパーテスト
# ============================================================

@patch("core.quality_gate_enhanced.check_strategic_refinement_quality")
@patch("core.schemas.refinement_schema.RefinedStrategicPlan")
def test_run_quality_gate_tool_returns_blocked(mock_plan_cls, mock_qg):
    """
    run_quality_gate ツールが check_strategic_refinement_quality を正しく呼び出し、
    blocked ステータスをJSON文字列で返すことを検証する。
    """
    from core.schemas.refinement_schema import DecisionGradeStatus

    # quality gate の戻り値モック
    mock_qg.return_value = DecisionGradeStatus(
        status="blocked",
        blocking_reasons=["必須入力項目が欠落しています: revenue_projection"],
        warnings=[],
    )
    # RefinedStrategicPlan のパースをモック
    mock_plan_cls.return_value = MagicMock()

    from core.agents_sdk.tools import run_quality_gate
    plan_json = json.dumps({"forecast_source": "assumption_only"})
    result = call_tool(run_quality_gate, plan_json=plan_json)

    assert result["status"] == "blocked"
    assert len(result["blocking_reasons"]) > 0


def test_run_quality_gate_tool_error_returns_blocked():
    """
    parse エラーや実行エラー時はフェイルセーフで status='blocked' を返す。
    """
    from core.agents_sdk.tools import run_quality_gate
    result = call_tool(run_quality_gate, plan_json="not-valid-json-{{{")
    assert result["status"] == "blocked"
    assert len(result["blocking_reasons"]) > 0


# ============================================================
# create_human_checkpoint ツールテスト
# ============================================================

@patch("core.supabase_client.get_supabase_client")
def test_create_human_checkpoint(mock_get_sb):
    """Skeptic Agent のブロック時に human_checkpoints へ INSERT する。"""
    mock_sb = MagicMock()
    mock_get_sb.return_value = mock_sb
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "checkpoint-001"}
    ]

    from core.agents_sdk.tools import create_human_checkpoint
    result = call_tool(
        create_human_checkpoint,
        pipeline_run_id="run-001",
        stage_output_id="stage-output-001",
        blocking_reasons_json=json.dumps(["数値不整合が検出されました"]),
    )

    assert result["checkpoint_id"] == "checkpoint-001"
    assert result["status"] == "pending"
    mock_sb.table.assert_called_with("human_checkpoints")
    insert_call = mock_sb.table.return_value.insert.call_args[0][0]
    assert insert_call["checkpoint_type"] == "skeptic_block"
    assert insert_call["pipeline_run_id"] == "run-001"
