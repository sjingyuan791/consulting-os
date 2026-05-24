from typing import Dict, Any, Optional, List
import logging
import json
from abc import ABC, abstractmethod

from core.llm_client import client as openai_client
from core.llm_router import LLMRouter
from core.rag_service import get_rag_service

logger = logging.getLogger(__name__)

class AgentResult:
    """エージェントの実行結果"""
    def __init__(self, narrative: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        self.narrative = narrative
        self.data = data
        self.metadata = metadata or {}

class BaseAgent(ABC):
    """
    Consulting MASのエージェント基底クラス。
    共通機能（LLM呼び出し、RAG検索、ログ出力）を提供する。
    """
    
    def __init__(self, client_id: str, model_name: str = "gpt-4o"):
        self.client_id = client_id
        self.model_name = model_name
        self.rag_service = get_rag_service()
        self.logger = logging.getLogger(f"agents.{self.__class__.__name__}")

    async def _call_llm(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        response_model: Optional[type] = None
    ) -> Any:
        """LLMを呼び出す共通メソッド"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            if response_model:
                completion = openai_client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=messages,
                    response_format=response_model
                )
                return completion.choices[0].message.parsed
            else:
                completion = openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
                return completion.choices[0].message.content

        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            raise

    def _get_rag_context(self, query: str) -> str:
        """RAGから関連情報を検索"""
        try:
            context = self.rag_service.get_context(self.client_id, query)
            return context if context else ""
        except Exception as e:
            self.logger.warning(f"RAG retrieval failed: {e}")
            return ""

    @abstractmethod
    async def run(self, context: Dict[str, Any]) -> AgentResult:
        """エージェントのメイン処理。サブクラスで実装必須。"""
        pass
