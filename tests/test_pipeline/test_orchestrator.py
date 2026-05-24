"""
Test Pipeline Orchestrator.
パイプラインオーケストレーターのテスト
"""
import pytest
import asyncio
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.pipeline.orchestrator import (
    PipelineOrchestrator, PipelineRun, StageOutput, HumanCheckpoint
)
from core.schemas.pipeline_stages import PipelineStatus, StageStatus, CheckpointType, CheckpointStatus


def run_async(coro):
    """Helper to run async coroutine in sync test"""
    return asyncio.run(coro)


class TestPipelineOrchestrator:
    """PipelineOrchestrator のテスト"""
    
    def test_orchestrator_creation(self):
        """オーケストレーターの作成"""
        with patch('core.pipeline.orchestrator.get_supabase_client'):
            orchestrator = PipelineOrchestrator()
        
            assert orchestrator is not None
            assert hasattr(orchestrator, '_engines')
    
    def test_register_engine(self):
        """エンジン登録"""
        with patch('core.pipeline.orchestrator.get_supabase_client'):
            orchestrator = PipelineOrchestrator()
            mock_engine = MagicMock()
            mock_engine.STAGE_NUMBER = 1
            
            orchestrator.register_engine(1, mock_engine)
            
            assert 1 in orchestrator._engines
            assert orchestrator._engines[1] == mock_engine
    
    def test_register_multiple_engines(self):
        """複数エンジンの登録"""
        with patch('core.pipeline.orchestrator.get_supabase_client'):
            orchestrator = PipelineOrchestrator()
            
            for i in range(1, 8):
                mock_engine = MagicMock()
                mock_engine.STAGE_NUMBER = i
                orchestrator.register_engine(i, mock_engine)
            
            assert len(orchestrator._engines) == 7


class TestPipelineModels:
    """パイプラインモデルのテスト"""
    
    def test_pipeline_run_model(self):
        """PipelineRunモデル"""
        run = PipelineRun(
            id="run-001",
            client_id="client-001",
            status=PipelineStatus.PENDING,
            version=1,
            current_stage=1,
            config_json={},
            created_at=datetime.now()
        )
        
        assert run.id == "run-001"
        assert run.status == PipelineStatus.PENDING
    
    def test_stage_output_model(self):
        """StageOutputモデル"""
        output = StageOutput(
            id="stage-001",
            pipeline_run_id="run-001",
            stage_number=1,
            stage_name="ROA Deductive Engine",
            input_json={"test": "data"},
            status=StageStatus.PENDING
        )
        
        assert output.stage_number == 1
        assert output.status == StageStatus.PENDING
    
    def test_human_checkpoint_model(self):
        """HumanCheckpointモデル"""
        checkpoint = HumanCheckpoint(
            id="cp-001",
            stage_output_id="stage-001",
            checkpoint_type=CheckpointType.ROOT_CAUSE_CONFIRMATION,
            status=CheckpointStatus.PENDING
        )
        
        assert checkpoint.checkpoint_type == CheckpointType.ROOT_CAUSE_CONFIRMATION


class TestPipelineStatuses:
    """パイプラインステータスのテスト"""
    
    def test_pipeline_status_enum(self):
        """PipelineStatus列挙型"""
        assert PipelineStatus.PENDING == "PENDING"
        assert PipelineStatus.RUNNING == "RUNNING"
        assert PipelineStatus.COMPLETED == "COMPLETED"
        assert PipelineStatus.FAILED == "FAILED"
    
    def test_stage_status_enum(self):
        """StageStatus列挙型"""
        assert StageStatus.PENDING == "PENDING"
        assert StageStatus.RUNNING == "RUNNING"
        assert StageStatus.COMPLETED == "COMPLETED"
    
    def test_checkpoint_status_enum(self):
        """CheckpointStatus列挙型"""
        assert CheckpointStatus.PENDING == "PENDING"
        assert CheckpointStatus.APPROVED == "APPROVED"
        assert CheckpointStatus.REJECTED == "REJECTED"


class TestOrchestratorHelpers:
    """オーケストレーターヘルパーメソッドのテスト"""
    
    def test_prepare_next_input(self):
        """次ステージ入力準備"""
        with patch('core.pipeline.orchestrator.get_supabase_client'):
            orchestrator = PipelineOrchestrator()
            
            current_result = MagicMock()
            current_result.model_dump.return_value = {"result": "data"}
            
            previous_input = {"original": "input"}
            
            result = orchestrator._prepare_next_input(current_result, previous_input)
            
            assert "original" in result
            assert "previous_stage_output" in result


class TestStageDefinitions:
    """ステージ定義のテスト"""
    
    def test_stages_defined(self):
        """7ステージが定義されている"""
        assert len(PipelineOrchestrator.STAGES) == 7
    
    def test_stage_names(self):
        """ステージ名が正しい"""
        stage_names = [s[1] for s in PipelineOrchestrator.STAGES]
        
        assert "ROA Deductive Engine" in stage_names
        assert "Root Cause Inductive Engine" in stage_names
    
    def test_stage_checkpoints(self):
        """チェックポイントが設定されている"""
        checkpoint_stages = [s for s in PipelineOrchestrator.STAGES if s[3] is not None]
        
        # Stage 3, 4, 5 にチェックポイントがある
        assert len(checkpoint_stages) == 3
