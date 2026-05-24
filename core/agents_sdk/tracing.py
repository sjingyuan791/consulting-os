"""
ConsultingOSTracingProcessor — SDK trace を DB に書くカスタムプロセッサ。

書込先:
- agent_steps テーブル: AgentSpanData 完了時（1エージェント実行=1行）
- llm_usage_log テーブル: GenerationSpanData 完了時（既存 record_llm_usage() 経由）

設計方針:
- on_span_end は例外を外に出さない（fire-and-forget）
- FunctionSpanData と GenerationSpanData は parent_id で AgentSpan へ集約
- trace.group_id = pipeline_run_id（SDKRunner が trace() 呼び出し時にセット）
"""
from __future__ import annotations

import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents import TracingProcessor, Trace, Span
from agents import AgentSpanData, FunctionSpanData, GenerationSpanData

logger = logging.getLogger("agents_sdk.tracing")


class ConsultingOSTracingProcessor(TracingProcessor):
    """
    SDK トレースイベントを Supabase の audit テーブルへ書き込む。

    Usage:
        from agents import add_trace_processor
        processor = ConsultingOSTracingProcessor(pipeline_run_id="uuid")
        add_trace_processor(processor)
    """

    def __init__(
        self,
        pipeline_run_id: Optional[str] = None,
        stage_number: Optional[int] = None,
        stage_name: Optional[str] = None,
    ):
        self._default_pipeline_run_id = pipeline_run_id
        self._stage_number = stage_number
        self._stage_name = stage_name
        self._sb: Any = None

        # trace_id → group_id (= pipeline_run_id) のマッピング
        self._trace_group_map: Dict[str, str] = {}
        # parent_span_id → [child entries] のバッファ（ツール呼び出し集約）
        self._tool_call_buffer: Dict[str, List[dict]] = {}

    # --- lazy Supabase client ---
    @property
    def sb(self) -> Any:
        if self._sb is None:
            from core.supabase_client import get_supabase_client
            self._sb = get_supabase_client()
        return self._sb

    # ---- TracingProcessor interface ----

    def on_trace_start(self, trace: Trace) -> None:
        """Trace 開始時に group_id を記録する。"""
        group_id = getattr(trace, "group_id", None)
        if group_id:
            self._trace_group_map[trace.trace_id] = str(group_id)

    def on_trace_end(self, trace: Trace) -> None:
        """Trace 完了時のクリーンアップ（今は何もしない）。"""
        logger.debug(
            "[Trace end] trace_id=%s name=%s group_id=%s",
            trace.trace_id,
            trace.name,
            getattr(trace, "group_id", None),
        )

    def on_span_start(self, span: Span) -> None:
        """Span 開始時は何もしない（on_span_end で一括処理）。"""

    def on_span_end(self, span: Span) -> None:
        """Span 完了時にルーティングして DB へ書く。"""
        try:
            data = span.span_data
            run_id = self._resolve_run_id(span)

            if isinstance(data, AgentSpanData):
                self._handle_agent_span(span, data, run_id)
            elif isinstance(data, GenerationSpanData):
                self._handle_generation_span(span, data, run_id)
            elif isinstance(data, FunctionSpanData):
                self._handle_function_span(span, data)
        except Exception as exc:
            # 絶対に例外を外に出さない
            logger.error(
                "[Tracing] on_span_end failed for span %s: %s: %s",
                getattr(span, "span_id", "?"),
                type(exc).__name__,
                exc,
            )

    def force_flush(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    # ---- private helpers ----

    def _resolve_run_id(self, span: Span) -> Optional[str]:
        """trace.group_id → pipeline_run_id を返す。なければデフォルト値。"""
        run_id = self._trace_group_map.get(span.trace_id)
        return run_id or self._default_pipeline_run_id

    def _handle_agent_span(
        self, span: Span, data: AgentSpanData, run_id: Optional[str]
    ) -> None:
        """AgentSpanData → agent_steps INSERT"""
        tool_calls = self._pop_tool_calls(span.span_id)

        payload = {
            "pipeline_run_id": run_id,
            "stage_number": self._stage_number,
            "stage_name": self._stage_name,
            "agent_name": data.name,
            "tool_calls_json": json.dumps(tool_calls, ensure_ascii=False),
            "output_json": json.dumps({}, ensure_ascii=False),
            "validations_json": json.dumps([], ensure_ascii=False),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            self.sb.table("agent_steps").insert(payload).execute()
        except Exception as exc:
            logger.error("[Tracing] agent_steps insert failed: %s", exc)

    def _handle_generation_span(
        self, span: Span, data: GenerationSpanData, run_id: Optional[str]
    ) -> None:
        """GenerationSpanData → llm_usage_log (record_llm_usage) + バッファ積み"""
        usage = data.usage or {}
        # usage は dict[str, Any] または Usage オブジェクトの可能性
        if isinstance(usage, dict):
            input_tokens = int(usage.get("input_tokens", 0))
            output_tokens = int(usage.get("output_tokens", 0))
        else:
            input_tokens = int(getattr(usage, "input_tokens", 0))
            output_tokens = int(getattr(usage, "output_tokens", 0))

        model = data.model or "unknown"

        if input_tokens or output_tokens:
            try:
                from core.llm_client import record_llm_usage
                record_llm_usage(
                    task_type="sdk_agent_generation",
                    model=model,
                    prompt_tokens=input_tokens,
                    completion_tokens=output_tokens,
                )
            except Exception as exc:
                logger.error("[Tracing] record_llm_usage failed: %s", exc)

        # 親 span のバッファへ積む
        parent_id = span.parent_id
        if parent_id:
            entry = {
                "type": "llm_generation",
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "span_id": span.span_id,
            }
            self._accumulate(parent_id, entry)

    def _handle_function_span(self, span: Span, data: FunctionSpanData) -> None:
        """FunctionSpanData → 親 span のバッファへ積む"""
        parent_id = span.parent_id
        if not parent_id:
            return

        entry = {
            "type": "function_call",
            "function_name": data.name,
            "input_snippet": str(data.input or "")[:500],
            "output_snippet": str(data.output or "")[:500],
            "span_id": span.span_id,
        }
        self._accumulate(parent_id, entry)

    def _accumulate(self, parent_id: str, entry: dict) -> None:
        self._tool_call_buffer.setdefault(parent_id, []).append(entry)

    def _pop_tool_calls(self, span_id: str) -> List[dict]:
        return self._tool_call_buffer.pop(span_id, [])


# ---- evidence helpers ----

def build_evidence_record(
    pipeline_run_id: str,
    claim_id: str,
    source_type: str,
    source_ref: str,
    snippet: str,
) -> dict:
    """
    evidence テーブル INSERT 用の dict を構築する。

    Args:
        claim_id: 主張の安定識別子（例: "section_13.revenue_y1"）
        source_type: 'financial_data' | 'market_data' | 'interview' | 'calculated' | 'inferred'
        source_ref: 参照元の説明（例: "financials.2024.sales"）
        snippet: エビデンステキスト（ハッシュ生成のみに使用）
    """
    return {
        "pipeline_run_id": pipeline_run_id,
        "claim_id": claim_id,
        "source_type": source_type,
        "source_ref": source_ref,
        "snippet_hash": hashlib.sha256(snippet.encode()).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def persist_evidence(pipeline_run_id: str, records: List[dict]) -> None:
    """evidence レコードを Supabase へ一括 INSERT する。"""
    if not records:
        return
    from core.supabase_client import get_supabase_client
    sb = get_supabase_client()
    try:
        sb.table("evidence").insert(records).execute()
    except Exception as exc:
        logger.error("[Evidence] Failed to insert %d records: %s", len(records), exc)
