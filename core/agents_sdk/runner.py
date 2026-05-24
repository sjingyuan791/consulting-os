"""
SDKRunner — OpenAI Agents SDK の非同期実行ラッパー。

責務:
- pipeline_run_id を trace.group_id にセットして監査を可能にする
- ConsultingOSTracingProcessor を登録して agent_steps / llm_usage_log に書く
- 既存 pipeline の async 構造に適合（await で呼び出し可能）
- add_trace_processor は毎回呼ばず set_trace_processors でリセットして多重登録を防ぐ
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from agents import Agent, Runner, trace
from agents import set_trace_processors

from core.agents_sdk.tracing import ConsultingOSTracingProcessor

logger = logging.getLogger("agents_sdk.runner")


class SDKRunner:
    """
    OpenAI Agents SDK の Agent を非同期実行するラッパー。

    Example:
        runner = SDKRunner(pipeline_run_id="uuid", stage_number=7)
        agent = create_writer_agent()
        result = await runner.run(agent, "章ID=1:\\n\\n{prompt}")
        output: WriterAgentOutput = result.final_output
    """

    def __init__(
        self,
        pipeline_run_id: Optional[str] = None,
        stage_number: Optional[int] = None,
        stage_name: Optional[str] = None,
    ) -> None:
        self.pipeline_run_id = pipeline_run_id
        self.stage_number = stage_number
        self.stage_name = stage_name
        self._tracer = ConsultingOSTracingProcessor(
            pipeline_run_id=pipeline_run_id,
            stage_number=stage_number,
            stage_name=stage_name,
        )

    async def run(
        self,
        agent: Agent,
        input_text: str,
        context_vars: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Agent を実行して RunResult を返す。

        Args:
            agent: 実行する Agent インスタンス。
            input_text: エージェントへの入力テキスト。
            context_vars: 追加コンテキスト（RunContextWrapper.context に渡る）。

        Returns:
            RunResult（result.final_output で型付き出力を取得）。
        """
        # トレーサーをセット（多重登録防止のため set_trace_processors で上書き）
        set_trace_processors([self._tracer])

        trace_name = f"consulting_os_{agent.name}"
        if self.pipeline_run_id:
            trace_name += f"_{self.pipeline_run_id[:8]}"

        logger.info(
            "[SDKRunner] Starting %s | pipeline_run_id=%s stage=%s",
            agent.name,
            self.pipeline_run_id,
            self.stage_number,
        )

        with trace(trace_name, group_id=self.pipeline_run_id):
            result = await Runner.run(
                agent,
                input_text,
                context=context_vars or {},
            )

        logger.info("[SDKRunner] Completed %s", agent.name)
        return result
