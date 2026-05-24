"""
Base Engine - Abstract base class for all pipeline stage engines.
Provides common functionality for execution, logging, and error handling.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TypeVar, Generic
from pydantic import BaseModel
from datetime import datetime
import logging
import time


# Type variables for input/output schemas
TInput = TypeVar('TInput', bound=BaseModel)
TOutput = TypeVar('TOutput', bound=BaseModel)


class EngineExecutionError(Exception):
    """Exception raised when engine execution fails."""
    def __init__(self, message: str, stage: str, recoverable: bool = False):
        self.message = message
        self.stage = stage
        self.recoverable = recoverable
        super().__init__(f"[{stage}] {message}")


class EngineConfig(BaseModel):
    """Configuration for engine execution."""
    max_retries: int = 3
    timeout_seconds: int = 300
    enable_caching: bool = True
    verbose_logging: bool = False
    

class ExecutionMetrics(BaseModel):
    """Metrics collected during engine execution."""
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time_ms: int = 0
    retry_count: int = 0
    llm_calls: int = 0
    tokens_used: int = 0
    

class BaseEngine(ABC, Generic[TInput, TOutput]):
    """
    Abstract base class for all pipeline stage engines.
    
    Each stage engine should:
    1. Inherit from this class
    2. Implement the `process` method
    3. Define input/output schema types
    """
    
    # Override in subclasses
    STAGE_NUMBER: int = 0
    STAGE_NAME: str = "Base Engine"
    
    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        self.logger = logging.getLogger(f"pipeline.{self.STAGE_NAME}")
        self.metrics = None
    
    @abstractmethod
    async def process(
        self, 
        input_data: TInput,
        previous_output: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TOutput:
        """
        Core processing logic for this stage.
        Must be implemented by each stage engine.
        
        Args:
            input_data: Validated input data for this stage
            previous_output: Output from the previous stage (if any)
            context: Additional context (client info, config, etc.)
            
        Returns:
            Validated output data for this stage
        """
        pass
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TOutput:
        """
        Execute the engine with error handling and metrics collection.
        
        This is the main entry point called by the orchestrator.
        """
        self.metrics = ExecutionMetrics(start_time=datetime.now())
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting {self.STAGE_NAME}")
            
            # Validate and convert input
            validated_input = self._validate_input(input_data)
            
            # Execute with retries
            result = await self._execute_with_retry(
                validated_input, 
                previous_output, 
                context
            )
            
            # Record metrics
            self.metrics.end_time = datetime.now()
            self.metrics.execution_time_ms = int((time.time() - start_time) * 1000)
            
            self.logger.info(
                f"Completed {self.STAGE_NAME} in {self.metrics.execution_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            self.metrics.end_time = datetime.now()
            self.metrics.execution_time_ms = int((time.time() - start_time) * 1000)
            
            self.logger.error(f"Failed {self.STAGE_NAME}: {type(e).__name__}")
            raise EngineExecutionError(
                message=str(e),
                stage=self.STAGE_NAME,
                recoverable=self._is_recoverable_error(e)
            )
    
    async def _execute_with_retry(
        self,
        input_data: TInput,
        previous_output: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> TOutput:
        """Execute with automatic retry on transient failures."""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await self.process(input_data, previous_output, context)
            except Exception as e:
                last_error = e
                self.metrics.retry_count += 1
                
                if not self._is_recoverable_error(e):
                    raise
                    
                self.logger.warning(
                    f"Retry {attempt + 1}/{self.config.max_retries} for {self.STAGE_NAME}"
                )
                
                # Exponential backoff
                await self._backoff(attempt)
        
        raise last_error
    
    async def _backoff(self, attempt: int):
        """Exponential backoff between retries."""
        import asyncio
        wait_time = min(2 ** attempt, 30)  # Max 30 seconds
        await asyncio.sleep(wait_time)
    
    def _validate_input(self, input_data: Dict[str, Any]) -> TInput:
        """Validate input data against schema. Override to customize."""
        return input_data  # Subclasses should implement proper validation
    
    def _is_recoverable_error(self, error: Exception) -> bool:
        """Determine if an error is recoverable (transient)."""
        recoverable_types = (
            TimeoutError,
            ConnectionError,
        )
        return isinstance(error, recoverable_types)
    
    def get_metrics(self) -> Optional[ExecutionMetrics]:
        """Get execution metrics."""
        return self.metrics


class DeterministicEngine(BaseEngine[TInput, TOutput]):
    """
    Base class for deterministic (non-AI) engines.
    These engines produce consistent outputs for the same inputs.
    """
    
    @abstractmethod
    async def compute(
        self,
        input_data: TInput,
        previous_output: Optional[Dict[str, Any]] = None
    ) -> TOutput:
        """Pure computation logic without AI."""
        pass
    
    async def process(
        self,
        input_data: TInput,
        previous_output: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TOutput:
        """Delegate to compute method."""
        return await self.compute(input_data, previous_output)


class AIEngine(BaseEngine[TInput, TOutput]):
    """
    Base class for AI-powered engines.
    These engines use LLM for analysis and generation.
    """
    
    def __init__(self, config: Optional[EngineConfig] = None):
        super().__init__(config)
        self._llm_client = None
    
    @property
    def llm_client(self):
        """Lazy-load LLM client."""
        if self._llm_client is None:
            from core.llm_client import get_llm_client
            self._llm_client = get_llm_client()
        return self._llm_client
    
    async def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[type] = None,
        temperature: float = 0.3
    ) -> Any:
        """
        Make an LLM call with metrics tracking.
        """
        self.metrics.llm_calls += 1
        
        try:
            # Import here to avoid circular dependency
            from core.llm_client import structured_llm_call
            
            result = await structured_llm_call(
                prompt=prompt,
                system_prompt=system_prompt,
                response_schema=response_schema,
                temperature=temperature
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"LLM call failed: {type(e).__name__}")
            raise
    
    @abstractmethod
    def build_prompt(
        self,
        input_data: TInput,
        previous_output: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the prompt for LLM. Must be implemented by subclasses."""
        pass
    
    def get_system_prompt(self) -> str:
        """Get system prompt for this engine. Override to customize."""
        return f"""あなたは戦略コンサルティングの専門家です。
{self.STAGE_NAME}フェーズを担当しています。
分析は論理的で、エビデンスに基づいた回答を提供してください。
出力は指定されたJSON形式に厳密に従ってください。"""
