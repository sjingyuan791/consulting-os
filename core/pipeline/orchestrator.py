"""
Pipeline Orchestrator - Main orchestration for 7-stage consulting pipeline.
Manages stage execution, checkpoints, lineage tracking, and error handling.
"""
from typing import Dict, Any, Optional, List, Tuple, Type
from datetime import datetime
from uuid import UUID
import logging
import asyncio

from core.pipeline.base_engine import BaseEngine, EngineExecutionError
from core.schemas.pipeline_stages import (
    PipelineStatus, StageStatus, CheckpointStatus, CheckpointType,
    Stage1Output, Stage2Output, Stage3Output, Stage4Output,
    Stage5Output, Stage6Output, Stage7Output
)
from core.supabase_client import get_supabase_client
from pydantic import BaseModel


class PipelineRun(BaseModel):
    """Pipeline run record."""
    id: str
    client_id: str
    status: PipelineStatus
    version: int
    current_stage: int
    config_json: Dict[str, Any]
    created_at: datetime
    created_by: Optional[str] = None


class StageOutput(BaseModel):
    """Stage output record."""
    id: str
    pipeline_run_id: str
    stage_number: int
    stage_name: str
    input_json: Dict[str, Any]
    output_json: Optional[Dict[str, Any]] = None
    status: StageStatus
    confidence_score: Optional[float] = None


class HumanCheckpoint(BaseModel):
    """Human checkpoint record."""
    id: str
    stage_output_id: str
    checkpoint_type: CheckpointType
    status: CheckpointStatus
    feedback_json: Optional[Dict[str, Any]] = None


class PipelineOrchestrator:
    """
    Main orchestrator for the 7-stage consulting pipeline.
    Manages stage execution, checkpoints, and lineage tracking.
    """
    
    # Stage definitions: (stage_number, name, engine_class, checkpoint_type)
    STAGES: List[Tuple[int, str, Optional[Type[BaseEngine]], Optional[CheckpointType]]] = [
        (1, "ROA Deductive Engine", None, None),
        (2, "Root Cause Inductive Engine", None, None),
        (3, "Hypothesis Verification Planner", None, CheckpointType.ROOT_CAUSE_CONFIRMATION),
        (4, "Strategy Design Engine", None, CheckpointType.STRATEGY_DIRECTION),
        (5, "HOW-Tree Tactical Generator", None, CheckpointType.TACTICAL_PRIORITIZATION),
        (6, "KPI & Financial Planning", None, None),
        (7, "Mid-Term Plan Generator", None, None),
    ]
    
    def __init__(self):
        self.sb = get_supabase_client()
        self.logger = logging.getLogger("pipeline.orchestrator")
        self._engines: Dict[int, BaseEngine] = {}
    
    def register_engine(self, stage_number: int, engine: BaseEngine):
        """Register an engine for a specific stage."""
        self._engines[stage_number] = engine
        self.logger.info(f"Registered engine for Stage {stage_number}")
    
    async def create_run(
        self,
        client_id: str,
        user_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> PipelineRun:
        """Create a new pipeline run."""
        # Get next version for this client
        version_res = self.sb.rpc("get_next_pipeline_version", {"p_client_id": client_id}).execute()
        version = version_res.data if version_res.data else 1
        
        payload = {
            "client_id": client_id,
            "version": version,
            "status": PipelineStatus.PENDING.value,
            "current_stage": 0,
            "config_json": config or {},
            "created_by": user_id
        }
        
        res = self.sb.table("pipeline_runs").insert(payload).execute()
        if not res.data:
            raise Exception("Failed to create pipeline run")
        
        return PipelineRun(**res.data[0])
    
    async def run_pipeline(
        self,
        client_id: str,
        financial_data: Dict[str, Any],
        operational_data: Dict[str, Any],
        market_data: Dict[str, Any],
        user_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> PipelineRun:
        """
        Execute the full consulting pipeline.
        
        Args:
            client_id: Client UUID
            financial_data: 3-year financial statements
            operational_data: Operational metrics
            market_data: Market/competitive data
            user_id: User initiating the run
            config: Pipeline configuration
            
        Returns:
            Completed pipeline run record
        """
        # 1. Create Pipeline Run
        run = await self.create_run(client_id, user_id, config)
        
        # 2. Update status to RUNNING
        await self._update_run_status(run.id, PipelineStatus.RUNNING)
        
        try:
            # 3. Prepare Initial Input
            current_input = {
                "financial_statements": financial_data,
                "operational_data": operational_data,
                "market_data": market_data,
                "client_id": client_id
            }
            previous_output = None
            
            # 4. Execute Stages Sequentially
            for stage_num, stage_name, _, checkpoint_type in self.STAGES:
                self.logger.info(f"Starting Stage {stage_num}: {stage_name}")
                
                # 4a. Create Stage Output Record
                stage_output = await self._create_stage_output(
                    pipeline_run_id=run.id,
                    stage_number=stage_num,
                    stage_name=stage_name,
                    input_json=current_input,
                    parent_output_id=previous_output.id if previous_output else None
                )
                
                # 4b. Execute Engine
                engine = self._engines.get(stage_num)
                if not engine:
                    self.logger.warning(f"No engine registered for Stage {stage_num}, skipping")
                    await self._update_stage_status(stage_output.id, StageStatus.SKIPPED)
                    continue
                
                try:
                    result = await engine.execute(
                        input_data=current_input,
                        previous_output=previous_output.output_json if previous_output else None,
                        context={"config": run.config_json, "client_id": client_id}
                    )
                    
                    # 4c. Save Output
                    await self._complete_stage_output(
                        stage_output.id,
                        output_json=result.model_dump() if hasattr(result, 'model_dump') else result,
                        confidence_score=getattr(result, 'confidence_score', 0.5)
                    )
                    
                except EngineExecutionError as e:
                    await self._fail_stage_output(stage_output.id, str(e))
                    await self._update_run_status(run.id, PipelineStatus.FAILED, str(e))
                    raise
                
                # 4d. Human Checkpoint (if required)
                if checkpoint_type:
                    checkpoint = await self._create_checkpoint(
                        stage_output_id=stage_output.id,
                        pipeline_run_id=run.id,
                        checkpoint_type=checkpoint_type
                    )
                    
                    # Update run status and wait for approval
                    await self._update_run_status(run.id, PipelineStatus.AWAITING_APPROVAL)
                    await self._update_run_current_stage(run.id, stage_num)
                    
                    # Return early - pipeline will resume when checkpoint is approved
                    self.logger.info(f"Awaiting approval for checkpoint: {checkpoint_type.value}")
                    return await self._get_run(run.id)
                
                # 4e. Update current stage and prepare next input
                await self._update_run_current_stage(run.id, stage_num)
                previous_output = stage_output
                current_input = self._prepare_next_input(result, current_input, stage_num)
            
            # 5. Pipeline Completed
            await self._update_run_status(run.id, PipelineStatus.COMPLETED)
            self.logger.info(f"Pipeline completed successfully: {run.id}")
            
            return await self._get_run(run.id)
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {type(e).__name__}: {e}")
            await self._update_run_status(run.id, PipelineStatus.FAILED, str(e))
            raise
    
    async def resume_pipeline(
        self,
        run_id: str,
        from_stage: int
    ) -> PipelineRun:
        """
        Resume a pipeline from a specific stage.
        Called after checkpoint approval.
        """
        run = await self._get_run(run_id)
        
        if run.status != PipelineStatus.AWAITING_APPROVAL:
            raise ValueError(f"Cannot resume pipeline in status: {run.status}")
        
        # Get the last completed stage output
        previous_output = await self._get_stage_output(run_id, from_stage)
        
        if not previous_output or not previous_output.output_json:
            raise ValueError(f"No output found for stage {from_stage}")
        
        # Update status
        await self._update_run_status(run_id, PipelineStatus.RUNNING)
        
        # Continue from next stage
        current_input = previous_output.output_json
        
        # Ensure we have stage_history if resuming from middle
        # (If previous_output.output_json was just the result, we might be missing context.
        # However, stage output usually contains the INPUT for the next stage if we are looking at *prepared* input.
        # Actually, previous_output.output_json is the OUTPUT of the stage.
        # The input for the NEXT stage needs not just the output of this stage, but the history.
        # Wait, run_pipeline logic:
        # current_input = ...
        # loop:
        #   result = engine.execute(input_data=current_input)
        #   current_input = _prepare_next_input(result, current_input)
        #
        # So when resuming, we need to reconstruct 'current_input' for the stage AFTER 'from_stage'.
        # The 'previous_output' (output of from_stage) has 'input_json' which was the input to 'from_stage'.
        # We can reconstruct.)
        
        # Reconstruct state
        # ideally we should store the 'next input' somewhere, or reconstruct it.
        # Simple reconstruction: take input of from_stage, add output of from_stage.
        
        reconstructed_input = self._prepare_next_input(
            # We need the actual result object or dict. output_json is dict.
            previous_output.output_json, 
            previous_output.input_json,
            from_stage
        )
        
        current_input = reconstructed_input
        
        for stage_num, stage_name, _, checkpoint_type in self.STAGES:
            if stage_num <= from_stage:
                continue  # Skip already completed stages
            
            self.logger.info(f"Resuming Stage {stage_num}: {stage_name}")
                
            # 4a. Create Stage Output Record
            stage_output = await self._create_stage_output(
                pipeline_run_id=run.id,
                stage_number=stage_num,
                stage_name=stage_name,
                input_json=current_input,
                parent_output_id=previous_output.id if previous_output else None
            )
            
            # 4b. Execute Engine
            engine = self._engines.get(stage_num)
            if not engine:
                self.logger.warning(f"No engine registered for Stage {stage_num}, skipping")
                await self._update_stage_status(stage_output.id, StageStatus.SKIPPED)
                continue
            
            try:
                result = await engine.execute(
                    input_data=current_input,
                    previous_output=previous_output.output_json if previous_output else None,
                    context={"config": run.config_json, "client_id": run.client_id}
                )
                
                # 4c. Save Output
                await self._complete_stage_output(
                    stage_output.id,
                    output_json=result.model_dump() if hasattr(result, 'model_dump') else result,
                    confidence_score=getattr(result, 'confidence_score', 0.5)
                )
                
            except EngineExecutionError as e:
                await self._fail_stage_output(stage_output.id, str(e))
                await self._update_run_status(run.id, PipelineStatus.FAILED, str(e))
                raise
            
            # 4d. Human Checkpoint (if required)
            if checkpoint_type:
                checkpoint = await self._create_checkpoint(
                    stage_output_id=stage_output.id,
                    pipeline_run_id=run.id,
                    checkpoint_type=checkpoint_type
                )
                
                # Update run status and wait for approval
                await self._update_run_status(run.id, PipelineStatus.AWAITING_APPROVAL)
                await self._update_run_current_stage(run.id, stage_num)
                
                # Return early - pipeline will resume when checkpoint is approved
                self.logger.info(f"Awaiting approval for checkpoint: {checkpoint_type.value}")
                return await self._get_run(run.id)
            
            # 4e. Update current stage and prepare next input
            await self._update_run_current_stage(run.id, stage_num)
            previous_output = stage_output
            current_input = self._prepare_next_input(result, current_input, stage_num)
            
        # 5. Pipeline Completed
        await self._update_run_status(run.id, PipelineStatus.COMPLETED)
        return await self._get_run(run.id)
    
    async def approve_checkpoint(
        self,
        checkpoint_id: str,
        user_id: str,
        decision: str,
        rationale: str,
        feedback: Optional[Dict[str, Any]] = None
    ) -> PipelineRun:
        """
        Approve or reject a human checkpoint.
        
        Args:
            checkpoint_id: Checkpoint UUID
            user_id: Approving user
            decision: "approve", "reject", or "revise"
            rationale: Reason for decision
            feedback: Optional feedback for revision
            
        Returns:
            Updated pipeline run
        """
        # Update checkpoint
        status = {
            "approve": CheckpointStatus.APPROVED,
            "reject": CheckpointStatus.REJECTED,
            "revise": CheckpointStatus.REVISION_REQUESTED
        }.get(decision, CheckpointStatus.REJECTED)
        
        self.sb.table("human_checkpoints").update({
            "status": status.value,
            "approved_by": user_id,
            "decision": decision,
            "rationale": rationale,
            "feedback_json": feedback or {},
            "decided_at": datetime.now().isoformat()
        }).eq("id", checkpoint_id).execute()
        
        # Get checkpoint details
        checkpoint_res = self.sb.table("human_checkpoints").select("*").eq("id", checkpoint_id).single().execute()
        checkpoint = checkpoint_res.data
        
        run_id = checkpoint["pipeline_run_id"]
        
        if decision == "approve":
            # Resume pipeline
            stage_output = await self._get_stage_output_by_id(checkpoint["stage_output_id"])
            return await self.resume_pipeline(run_id, stage_output.stage_number)
        elif decision == "reject":
            await self._update_run_status(run_id, PipelineStatus.CANCELLED)
            return await self._get_run(run_id)
        else:  # revise
            # Re-run the stage with feedback
            return await self._rerun_stage_with_feedback(run_id, checkpoint, feedback)
    
    def _prepare_next_input(
        self,
        current_result: Any,
        previous_input: Dict[str, Any],
        stage_number: int
    ) -> Dict[str, Any]:
        """Prepare input for the next stage."""
        result_dict = current_result.model_dump() if hasattr(current_result, 'model_dump') else current_result
        
        # Accumulate stage history
        stage_history = previous_input.get("stage_history", {}).copy()
        stage_history[str(stage_number)] = result_dict
        
        return {
            **previous_input,
            "previous_stage_output": result_dict,
            "stage_history": stage_history
        }
    
    # Database helper methods
    
    async def _get_run(self, run_id: str) -> PipelineRun:
        res = self.sb.table("pipeline_runs").select("*").eq("id", run_id).single().execute()
        return PipelineRun(**res.data)
    
    async def _update_run_status(
        self, 
        run_id: str, 
        status: PipelineStatus,
        error_message: Optional[str] = None
    ):
        payload = {"status": status.value}
        if error_message:
            payload["error_message"] = error_message
        if status == PipelineStatus.COMPLETED:
            payload["completed_at"] = datetime.now().isoformat()
        if status == PipelineStatus.RUNNING:
            payload["started_at"] = datetime.now().isoformat()
        self.sb.table("pipeline_runs").update(payload).eq("id", run_id).execute()
    
    async def _update_run_current_stage(self, run_id: str, stage: int):
        self.sb.table("pipeline_runs").update({"current_stage": stage}).eq("id", run_id).execute()
    
    async def _create_stage_output(
        self,
        pipeline_run_id: str,
        stage_number: int,
        stage_name: str,
        input_json: Dict[str, Any],
        parent_output_id: Optional[str] = None
    ) -> StageOutput:
        payload = {
            "pipeline_run_id": pipeline_run_id,
            "stage_number": stage_number,
            "stage_name": stage_name,
            "input_json": input_json,
            "parent_stage_output_id": parent_output_id,
            "status": StageStatus.RUNNING.value,
            "started_at": datetime.now().isoformat()
        }
        res = self.sb.table("stage_outputs").insert(payload).execute()
        return StageOutput(**res.data[0])
    
    async def _complete_stage_output(
        self,
        stage_id: str,
        output_json: Dict[str, Any],
        confidence_score: float
    ):
        self.sb.table("stage_outputs").update({
            "output_json": output_json,
            "status": StageStatus.COMPLETED.value,
            "confidence_score": confidence_score,
            "completed_at": datetime.now().isoformat()
        }).eq("id", stage_id).execute()
    
    async def _fail_stage_output(self, stage_id: str, error: str):
        self.sb.table("stage_outputs").update({
            "status": StageStatus.FAILED.value,
            "metadata_json": {"error": error},
            "completed_at": datetime.now().isoformat()
        }).eq("id", stage_id).execute()
    
    async def _update_stage_status(self, stage_id: str, status: StageStatus):
        self.sb.table("stage_outputs").update({
            "status": status.value,
            "completed_at": datetime.now().isoformat()
        }).eq("id", stage_id).execute()
    
    async def _get_stage_output(self, run_id: str, stage_number: int) -> Optional[StageOutput]:
        res = self.sb.table("stage_outputs").select("*").eq("pipeline_run_id", run_id).eq("stage_number", stage_number).execute()
        return StageOutput(**res.data[0]) if res.data else None
    
    async def _get_stage_output_by_id(self, stage_id: str) -> StageOutput:
        res = self.sb.table("stage_outputs").select("*").eq("id", stage_id).single().execute()
        return StageOutput(**res.data)
    
    async def _create_checkpoint(
        self,
        stage_output_id: str,
        pipeline_run_id: str,
        checkpoint_type: CheckpointType
    ) -> HumanCheckpoint:
        checkpoint_names = {
            CheckpointType.ROOT_CAUSE_CONFIRMATION: "根本原因の確認",
            CheckpointType.STRATEGY_DIRECTION: "戦略方針の承認",
            CheckpointType.TACTICAL_PRIORITIZATION: "施策優先度の決定"
        }
        
        payload = {
            "stage_output_id": stage_output_id,
            "pipeline_run_id": pipeline_run_id,
            "checkpoint_type": checkpoint_type.value,
            "checkpoint_name": checkpoint_names.get(checkpoint_type, checkpoint_type.value),
            "status": CheckpointStatus.PENDING.value,
            "notification_sent_at": datetime.now().isoformat()
        }
        res = self.sb.table("human_checkpoints").insert(payload).execute()
        return HumanCheckpoint(**res.data[0])
    
    async def _rerun_stage_with_feedback(
        self,
        run_id: str,
        checkpoint: Dict,
        feedback: Optional[Dict[str, Any]]
    ) -> PipelineRun:
        """Re-run a stage with revision feedback."""
        # Get the stage that needs revision
        stage_output = await self._get_stage_output_by_id(checkpoint["stage_output_id"])
        
        # Add feedback to input and re-execute
        revised_input = {
            **stage_output.input_json,
            "revision_feedback": feedback
        }
        
        # This would trigger re-execution of the stage
        # Implementation would depend on specific requirements
        
        return await self._get_run(run_id)


# Singleton instance
_orchestrator: Optional[PipelineOrchestrator] = None

def get_orchestrator() -> PipelineOrchestrator:
    """Get the singleton PipelineOrchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineOrchestrator()
    return _orchestrator
