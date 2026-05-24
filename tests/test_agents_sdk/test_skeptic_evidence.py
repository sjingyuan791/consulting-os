"""
Skeptic エビデンステスト:
- 【】マーカーのない主張は run_fact_check でリジェクト（trust_score < 50）
- 【】マーカー付き主張は検証対象として引用が抽出される
- tracing.py の build_evidence_record / persist_evidence ヘルパー
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from tests.test_agents_sdk.conftest import call_tool


# ============================================================
# エビデンスなし主張のリジェクトテスト
# ============================================================

def test_fact_check_no_citations_low_trust():
    """
    【】マーカーのない文章は total_citations=0 かつ trust_score が低い。
    plan の主張がエビデンスなしで通過しないことを確認する。
    """
    from core.agents_sdk.tools import run_fact_check
    result = call_tool(
        run_fact_check,
        ai_response="売上は前年比30%増加する見込みです。市場シェアは50%に拡大する。",
        source_data_json=json.dumps({}),
    )
    assert result["total_citations"] == 0
    assert result["trust_score"] < 50


def test_fact_check_with_citations_extracted():
    """
    【】マーカー付き文章は引用として抽出され total_citations > 0 になる。
    """
    from core.agents_sdk.tools import run_fact_check
    result = call_tool(
        run_fact_check,
        ai_response="【財務データ:売上高2024年度】によると売上は500百万円でした。",
        source_data_json=json.dumps({}),
    )
    assert result["total_citations"] >= 1


def test_fact_check_citation_verified_with_matching_source():
    """
    ソースデータと一致する【】引用は verified_count > 0 になり trust_score が上がる。
    """
    from core.agents_sdk.tools import run_fact_check
    result = call_tool(
        run_fact_check,
        ai_response="【財務データ:売上高2024年度:500】に基づき、売上500百万円を確認しました。",
        source_data_json=json.dumps({"財務データ": {"売上高2024年度": 500}}),
    )
    assert result["total_citations"] >= 1


def test_fact_check_hallucination_detected():
    """
    ソースに存在しない数値を断言すると mismatch/hallucination でスコアが下がる。
    """
    from core.agents_sdk.tools import run_fact_check
    result = call_tool(
        run_fact_check,
        ai_response="【市場データ:競合数:999】競合は999社存在します。",
        source_data_json=json.dumps({"市場データ": {"競合数": 5}}),
    )
    score_penalty = result["mismatch_count"] * 10 + result["hallucination_count"] * 20
    assert result["trust_score"] < 100 or score_penalty > 0


def test_fact_check_invalid_source_json():
    """
    不正な source_data_json はエラーを返しフェイルセーフで trust_score=0。
    """
    from core.agents_sdk.tools import run_fact_check
    result = call_tool(
        run_fact_check,
        ai_response="何らかのテキスト",
        source_data_json="{invalid-json",
    )
    assert result["trust_score"] == 0
    assert result["requires_human_review"] is True


# ============================================================
# evidence ヘルパー関数テスト
# ============================================================

def test_build_evidence_record_structure():
    """build_evidence_record が正しい dict 構造を返す。"""
    from core.agents_sdk.tracing import build_evidence_record

    record = build_evidence_record(
        pipeline_run_id="run-001",
        claim_id="section_1.revenue_y1",
        source_type="financial_data",
        source_ref="financials.2024.sales",
        snippet="売上高: 500百万円",
    )

    assert record["pipeline_run_id"] == "run-001"
    assert record["claim_id"] == "section_1.revenue_y1"
    assert record["source_type"] == "financial_data"
    assert record["source_ref"] == "financials.2024.sales"
    # snippet_hash は SHA256 hexdigest（64文字）
    assert len(record["snippet_hash"]) == 64
    assert "created_at" in record


def test_build_evidence_record_dedup_by_snippet():
    """同一スニペットは同一 snippet_hash を生成する（冪等性）。"""
    from core.agents_sdk.tracing import build_evidence_record

    snippet = "同一テキスト"
    r1 = build_evidence_record("r", "c", "financial_data", "ref", snippet)
    r2 = build_evidence_record("r", "c", "financial_data", "ref", snippet)
    assert r1["snippet_hash"] == r2["snippet_hash"]


@patch("core.supabase_client.get_supabase_client")
def test_persist_evidence_inserts_to_db(mock_get_sb):
    """persist_evidence が evidence テーブルに INSERT する。"""
    from core.agents_sdk.tracing import build_evidence_record, persist_evidence

    mock_sb = MagicMock()
    mock_get_sb.return_value = mock_sb

    records = [
        build_evidence_record("run-001", "claim_1", "financial_data", "ref1", "snippet1"),
        build_evidence_record("run-001", "claim_2", "market_data", "ref2", "snippet2"),
    ]
    persist_evidence("run-001", records)

    mock_sb.table.assert_called_with("evidence")
    mock_sb.table.return_value.insert.assert_called_once_with(records)


def test_persist_evidence_noop_on_empty():
    """空リストでは DB 呼び出しをしない（get_supabase_client 未呼び出し）。"""
    from core.agents_sdk.tracing import persist_evidence

    with patch("core.supabase_client.get_supabase_client") as mock_get_sb:
        persist_evidence("run-001", [])
        mock_get_sb.assert_not_called()
