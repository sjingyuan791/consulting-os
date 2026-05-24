"""
Tracing テスト:
- AgentSpanData で on_span_end → agent_steps に INSERT
- GenerationSpanData で on_span_end → record_llm_usage が呼ばれる
- FunctionSpanData がバッファに積まれ AgentSpan で集約される
- pipeline_run_id が trace.group_id から正しく解決される
"""
import json
import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# ヘルパー: モック Span / Trace ビルダー
# ============================================================

def _make_trace(trace_id: str, group_id: str = None):
    t = MagicMock()
    t.trace_id = trace_id
    t.name = "test_trace"
    t.group_id = group_id
    return t


def _make_span(span_id: str, trace_id: str, span_data, parent_id: str = None):
    s = MagicMock()
    s.span_id = span_id
    s.trace_id = trace_id
    s.parent_id = parent_id
    s.span_data = span_data
    return s


# ============================================================
# AgentSpanData → agent_steps INSERT テスト
# ============================================================

@patch("core.supabase_client.get_supabase_client")
def test_agent_span_persisted_to_db(mock_get_sb):
    """
    on_span_end に AgentSpanData を渡すと agent_steps テーブルへ INSERT される。
    """
    from agents import AgentSpanData
    from core.agents_sdk.tracing import ConsultingOSTracingProcessor

    mock_sb = MagicMock()
    mock_get_sb.return_value = mock_sb
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "step-001"}
    ]

    processor = ConsultingOSTracingProcessor(pipeline_run_id="test-run-123")

    trace = _make_trace("trace-001", group_id="test-run-123")
    processor.on_trace_start(trace)

    agent_data = AgentSpanData(name="WriterAgent")
    span = _make_span("span-001", "trace-001", agent_data)
    processor.on_span_end(span)

    mock_sb.table.assert_called_with("agent_steps")
    mock_sb.table.return_value.insert.assert_called_once()

    call_payload = mock_sb.table.return_value.insert.call_args[0][0]
    assert call_payload["agent_name"] == "WriterAgent"
    assert call_payload["pipeline_run_id"] == "test-run-123"


@patch("core.supabase_client.get_supabase_client")
def test_agent_span_uses_default_run_id_when_no_trace_group(mock_get_sb):
    """
    trace.group_id が未設定でも default_pipeline_run_id が使われる。
    """
    from agents import AgentSpanData
    from core.agents_sdk.tracing import ConsultingOSTracingProcessor

    mock_sb = MagicMock()
    mock_get_sb.return_value = mock_sb

    processor = ConsultingOSTracingProcessor(pipeline_run_id="default-run-id")

    trace = _make_trace("trace-002", group_id=None)
    processor.on_trace_start(trace)

    agent_data = AgentSpanData(name="CFOAgent")
    span = _make_span("span-002", "trace-002", agent_data)
    processor.on_span_end(span)

    call_payload = mock_sb.table.return_value.insert.call_args[0][0]
    assert call_payload["pipeline_run_id"] == "default-run-id"
    assert call_payload["agent_name"] == "CFOAgent"


# ============================================================
# GenerationSpanData → record_llm_usage テスト
# ============================================================

@patch("core.supabase_client.get_supabase_client")
@patch("core.llm_client.record_llm_usage")
def test_generation_span_calls_record_llm_usage(mock_record_fn, mock_get_sb):
    """
    GenerationSpanData のある span が on_span_end に来ると record_llm_usage が呼ばれる。
    """
    from agents import GenerationSpanData
    from core.agents_sdk.tracing import ConsultingOSTracingProcessor

    mock_sb = MagicMock()
    mock_get_sb.return_value = mock_sb

    processor = ConsultingOSTracingProcessor(pipeline_run_id="test-run-gen")

    trace = _make_trace("trace-003", group_id="test-run-gen")
    processor.on_trace_start(trace)

    gen_data = MagicMock(spec=GenerationSpanData)
    gen_data.model = "gpt-4o"
    gen_data.usage = {"input_tokens": 100, "output_tokens": 50}
    gen_span = _make_span("span-gen-001", "trace-003", gen_data, parent_id="span-agent-001")

    processor.on_span_end(gen_span)

    mock_record_fn.assert_called_once_with(
        task_type="sdk_agent_generation",
        model="gpt-4o",
        prompt_tokens=100,
        completion_tokens=50,
    )


# ============================================================
# FunctionSpanData → バッファ集約テスト
# ============================================================

@patch("core.supabase_client.get_supabase_client")
def test_function_span_accumulated_in_agent_step(mock_get_sb):
    """
    FunctionSpanData が先に来てバッファへ積まれ、
    その後 AgentSpan が来ると tool_calls_json に含まれる。
    """
    from agents import AgentSpanData, FunctionSpanData
    from core.agents_sdk.tracing import ConsultingOSTracingProcessor

    mock_sb = MagicMock()
    mock_get_sb.return_value = mock_sb

    processor = ConsultingOSTracingProcessor(pipeline_run_id="run-func-test")

    trace = _make_trace("trace-004", group_id="run-func-test")
    processor.on_trace_start(trace)

    # FunctionSpan（parent = agent span id）
    func_data = MagicMock(spec=FunctionSpanData)
    func_data.name = "python_reconcile_financials"
    func_data.input = '{"total_assets": 1000}'
    func_data.output = '{"passed": true}'
    func_span = _make_span("span-fn-001", "trace-004", func_data, parent_id="span-agent-002")
    processor.on_span_end(func_span)

    # AgentSpan
    agent_data = AgentSpanData(name="CFOAgent")
    agent_span = _make_span("span-agent-002", "trace-004", agent_data)
    processor.on_span_end(agent_span)

    call_payload = mock_sb.table.return_value.insert.call_args[0][0]
    tool_calls = json.loads(call_payload["tool_calls_json"])
    assert len(tool_calls) == 1
    assert tool_calls[0]["function_name"] == "python_reconcile_financials"
    assert tool_calls[0]["type"] == "function_call"


# ============================================================
# on_span_end の例外隔離テスト
# ============================================================

def test_on_span_end_does_not_raise_on_error():
    """
    on_span_end 内でエラーが発生しても例外が外に伝播しない（fire-and-forget）。
    """
    from core.agents_sdk.tracing import ConsultingOSTracingProcessor

    processor = ConsultingOSTracingProcessor(pipeline_run_id="run-err-test")

    bad_span = MagicMock()
    bad_span.span_id = "bad-span"
    bad_span.trace_id = "bad-trace"
    bad_span.parent_id = None
    bad_span.span_data = None  # isinstance チェックを全て失敗させる

    try:
        processor.on_span_end(bad_span)
    except Exception as e:
        pytest.fail(f"on_span_end raised an exception: {e}")


# ============================================================
# stage_number / stage_name が payload に含まれるテスト
# ============================================================

@patch("core.supabase_client.get_supabase_client")
def test_stage_metadata_in_agent_step_payload(mock_get_sb):
    """SDKRunner から渡された stage_number / stage_name が INSERT payload に入る。"""
    from agents import AgentSpanData
    from core.agents_sdk.tracing import ConsultingOSTracingProcessor

    mock_sb = MagicMock()
    mock_get_sb.return_value = mock_sb

    processor = ConsultingOSTracingProcessor(
        pipeline_run_id="run-stage-test",
        stage_number=7,
        stage_name="midterm_plan_writer",
    )

    trace = _make_trace("trace-005", group_id="run-stage-test")
    processor.on_trace_start(trace)

    agent_data = AgentSpanData(name="WriterAgent")
    span = _make_span("span-stage-001", "trace-005", agent_data)
    processor.on_span_end(span)

    call_payload = mock_sb.table.return_value.insert.call_args[0][0]
    assert call_payload["stage_number"] == 7
    assert call_payload["stage_name"] == "midterm_plan_writer"
