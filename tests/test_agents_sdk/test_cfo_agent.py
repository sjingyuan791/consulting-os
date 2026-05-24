"""
CFO Agent テスト:
- financials_verified=False のとき Agent が分析を実行しない
- python_reconcile_financials の整合性チェック
"""
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from core.agents_sdk.schemas import CFOAgentOutput
from tests.test_agents_sdk.conftest import call_tool


# ============================================================
# python_reconcile_financials のユニットテスト（DB不要）
# ============================================================

def test_reconcile_balanced_financials(sample_financials_dict):
    """整合する財務データは passed=True を返す。"""
    from core.agents_sdk.tools import python_reconcile_financials
    result = call_tool(python_reconcile_financials,
                       financials_json=json.dumps(sample_financials_dict))
    assert result["passed"] is True
    assert result["errors"] == []


def test_reconcile_bs_mismatch(broken_financials_dict):
    """BS不一致データは passed=False でエラーメッセージを返す。"""
    from core.agents_sdk.tools import python_reconcile_financials
    result = call_tool(python_reconcile_financials,
                       financials_json=json.dumps(broken_financials_dict))
    assert result["passed"] is False
    assert any("BS" in e for e in result["errors"])


def test_reconcile_invalid_json():
    """不正 JSON は passed=False でエラーを返す。"""
    from core.agents_sdk.tools import python_reconcile_financials
    result = call_tool(python_reconcile_financials, financials_json="not-json")
    assert result["passed"] is False
    assert any("JSON" in e or "parse" in e.lower() for e in result["errors"])


def test_reconcile_gross_profit_mismatch():
    """粗利不一致（sales - cogs ≠ gross_profit）は passed=False。"""
    from core.agents_sdk.tools import python_reconcile_financials
    data = {
        "total_assets": 1000.0,
        "total_liabilities": 600.0,
        "net_assets": 400.0,
        "sales": 500.0,
        "cogs": 300.0,
        "gross_profit": 100.0,  # 正しくは 200
    }
    result = call_tool(python_reconcile_financials,
                       financials_json=json.dumps(data))
    assert result["passed"] is False
    assert any("粗利" in e or "gross" in e.lower() for e in result["errors"])


# ============================================================
# get_financials_verified のユニットテスト（DB モック）
# ============================================================

@patch("core.supabase_client.get_supabase_client")
def test_get_financials_verified_true(mock_get_sb):
    """pipeline_run が存在し verified=True の場合。"""
    mock_sb = MagicMock()
    mock_get_sb.return_value = mock_sb

    # pipeline_runs → client_id
    mock_sb.table.return_value.select.return_value.eq.return_value\
        .limit.return_value.execute.return_value.data = [{"client_id": "client-001"}]
    # analysis_runs → financials_verified=True
    mock_sb.table.return_value.select.return_value.eq.return_value\
        .order.return_value.limit.return_value.execute.return_value.data = [
            {"financials_verified": True}
        ]

    from core.agents_sdk.tools import get_financials_verified
    result = call_tool(get_financials_verified, pipeline_run_id="test-run-id")

    assert result["financials_verified"] is True


@patch("core.supabase_client.get_supabase_client")
def test_get_financials_verified_false_when_not_found(mock_get_sb):
    """pipeline_run が見つからない場合はフェイルセーフで False を返す。"""
    mock_sb = MagicMock()
    mock_get_sb.return_value = mock_sb

    mock_sb.table.return_value.select.return_value.eq.return_value\
        .limit.return_value.execute.return_value.data = []

    from core.agents_sdk.tools import get_financials_verified
    result = call_tool(get_financials_verified, pipeline_run_id="nonexistent-run-id")

    assert result["financials_verified"] is False


# ============================================================
# CFO Agent 統合: verified=False でブロックを確認
# ============================================================

@patch("core.agents_sdk.runner.Runner")
@patch("core.agents_sdk.runner.set_trace_processors")
@patch("core.agents_sdk.runner.trace")
def test_cfo_agent_blocked_when_not_verified(mock_trace, mock_set_procs, mock_runner_cls,
                                              run_async):
    """
    financials_verified=False のとき CFO Agent は analysis=None を返す。
    Runner.run をモックして SDKRunner の非同期ラッパーをテスト。
    """
    mock_output = CFOAgentOutput(
        financials_verified=False,
        analysis=None,
        missing_inputs=["financials_verified"],
    )

    # Runner.run の async モック
    mock_runner_cls.run = AsyncMock(return_value=MagicMock(final_output=mock_output))

    # trace() のコンテキストマネージャをモック
    mock_trace.return_value.__enter__ = MagicMock(return_value=None)
    mock_trace.return_value.__exit__ = MagicMock(return_value=False)

    from core.agents_sdk.runner import SDKRunner
    from core.agents_sdk.agents_definitions import create_cfo_agent

    runner = SDKRunner(pipeline_run_id="test-run-cfo")
    agent = create_cfo_agent()
    result = run_async(runner.run(agent, "Analyze financials for pipeline test-run-cfo"))

    output: CFOAgentOutput = result.final_output
    assert output.financials_verified is False
    assert "financials_verified" in output.missing_inputs
    assert output.analysis is None
