"""
RAG Service - Unified RAG Operations with LLM Integration.
Combines indexing, retrieval, and LLM-powered responses with source citations.
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json

from openai import OpenAI
from core.config import Config
from core.rag_indexer import RAGIndexer, SourceType, IndexingResult
from core.rag_retriever import RAGRetriever, SearchConfig, SearchStrategy, RetrievalResult

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=Config.OPENAI_API_KEY)


@dataclass
class Citation:
    """Source citation for AI response."""
    source_name: str
    source_type: str
    relevance: float
    excerpt: str


@dataclass
class RAGResponse:
    """AI response with RAG context and citations."""
    answer: str
    citations: List[Citation]
    context_used: bool
    confidence_score: float
    model_used: str
    retrieval_info: Optional[Dict[str, Any]] = None


@dataclass
class RAGChainConfig:
    """Configuration for RAG chain."""
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 2000
    include_citations: bool = True
    min_confidence_threshold: float = 0.3
    context_max_tokens: int = 3000
    system_prompt_template: str = """あなたは経営コンサルタントのAIアシスタントです。
提供されたコンテキスト情報を活用して、正確で実践的なアドバイスを提供してください。

コンテキスト情報がある場合は、それを優先的に参照してください。
コンテキストに関連情報がない場合は、一般的な知識で回答しても構いませんが、
その旨を明示してください。

重要: 回答には必ず根拠を示し、具体的な数値や事実がある場合は引用してください。"""


class RAGService:
    """
    Unified RAG Service combining indexing, retrieval, and LLM responses.
    
    Usage:
        service = RAGService()
        
        # Index documents
        service.index_document(client_id, content, "csv", "financial_data.csv")
        
        # Query with RAG
        response = service.query(client_id, "売上の傾向を教えてください")
        print(response.answer)
        print(response.citations)
    """
    
    def __init__(
        self,
        chain_config: Optional[RAGChainConfig] = None,
        search_config: Optional[SearchConfig] = None
    ):
        self.chain_config = chain_config or RAGChainConfig()
        self.indexer = RAGIndexer()
        self.retriever = RAGRetriever(search_config)
    
    # ==========================================
    # Indexing Operations
    # ==========================================
    
    def index_document(
        self,
        client_id: str,
        content: str,
        source_type: str,
        source_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IndexingResult:
        """
        Index a document for RAG retrieval.
        
        Args:
            client_id: Client UUID
            content: Document content
            source_type: Type ('csv', 'pdf', 'text', 'manual')
            source_name: Document name
            metadata: Additional metadata
            
        Returns:
            IndexingResult with success status
        """
        st = SourceType(source_type) if source_type in [t.value for t in SourceType] else SourceType.MANUAL
        return self.indexer.index_document(
            client_id=client_id,
            content=content,
            source_type=st,
            source_name=source_name,
            metadata=metadata
        )
    
    def index_csv(
        self,
        client_id: str,
        csv_content: str,
        filename: str
    ) -> IndexingResult:
        """Index CSV content."""
        return self.indexer.index_csv_content(client_id, csv_content, filename)
    
    def index_pdf(
        self,
        client_id: str,
        pdf_file: Any,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IndexingResult:
        """Index PDF content."""
        return self.indexer.index_pdf(client_id, pdf_file, filename, metadata)
    
    
    def delete_document(self, client_id: str, source_name: str) -> int:
        """Delete a document from the index."""
        return self.indexer.delete_document(client_id, source_name)
    
    def list_documents(self, client_id: str) -> List[Dict[str, Any]]:
        """List all indexed documents for a client."""
        return self.indexer.list_indexed_documents(client_id)
    
    def get_document_count(self, client_id: str) -> int:
        """Get total chunk count for a client."""
        return self.indexer.get_document_count(client_id)
    
    # ==========================================
    # Retrieval Operations
    # ==========================================
    
    def search(
        self,
        client_id: str,
        query: str,
        match_count: int = 5
    ) -> RetrievalResult:
        """
        Search for relevant documents.
        
        Returns:
            RetrievalResult with ranked documents
        """
        return self.retriever.search(query, client_id, match_count=match_count)
    
    def get_context(
        self,
        client_id: str,
        query: str,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Get formatted context string for LLM.
        
        Returns:
            Formatted context with source citations
        """
        max_tok = max_tokens or self.chain_config.context_max_tokens
        return self.retriever.retrieve_context(query, client_id, max_tokens=max_tok)
    
    # ==========================================
    # LLM Operations with RAG
    # ==========================================
    
    def query(
        self,
        client_id: str,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        additional_context: Optional[str] = None
    ) -> RAGResponse:
        """
        Answer a question using RAG.
        
        Args:
            client_id: Client UUID
            question: User question
            conversation_history: Optional chat history
            additional_context: Additional context to include
            
        Returns:
            RAGResponse with answer and citations
        """
        # 1. Retrieve relevant context
        retrieval = self.retriever.search(question, client_id)
        context = self.retriever.retrieve_context(
            question,
            client_id,
            max_tokens=self.chain_config.context_max_tokens
        )
        
        # 2. Build messages
        system_prompt = self.chain_config.system_prompt_template
        
        if context:
            system_prompt += f"\n\n[参照コンテキスト]\n{context}"
        
        if additional_context:
            system_prompt += f"\n\n[追加情報]\n{additional_context}"
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Last 10 messages
        
        messages.append({"role": "user", "content": question})
        
        # 3. Generate response
        try:
            response = client.chat.completions.create(
                model=self.chain_config.model,
                messages=messages,
                temperature=self.chain_config.temperature,
                max_tokens=self.chain_config.max_tokens
            )
            
            answer = response.choices[0].message.content
            
            # 4. Build citations
            citations = []
            if self.chain_config.include_citations and retrieval.results:
                for result in retrieval.results[:3]:
                    citations.append(Citation(
                        source_name=result.source_name,
                        source_type=result.source_type,
                        relevance=result.similarity,
                        excerpt=result.content[:200] + "..." if len(result.content) > 200 else result.content
                    ))
            
            # 5. Calculate confidence
            avg_similarity = sum(r.similarity for r in retrieval.results) / len(retrieval.results) if retrieval.results else 0
            confidence = min(1.0, avg_similarity + 0.2) if context else 0.5
            
            return RAGResponse(
                answer=answer,
                citations=citations,
                context_used=bool(context),
                confidence_score=confidence,
                model_used=self.chain_config.model,
                retrieval_info={
                    "chunks_retrieved": len(retrieval.results),
                    "search_time_ms": retrieval.search_time_ms,
                    "strategy": retrieval.strategy_used.value
                }
            )
            
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return RAGResponse(
                answer=f"エラーが発生しました: {str(e)}",
                citations=[],
                context_used=False,
                confidence_score=0.0,
                model_used=self.chain_config.model
            )
    
    def query_with_structured_output(
        self,
        client_id: str,
        question: str,
        output_schema: type,
        additional_context: Optional[str] = None
    ) -> Any:
        """
        Query with structured output using Pydantic schema.
        
        Args:
            client_id: Client UUID
            question: User question
            output_schema: Pydantic model for response
            additional_context: Additional context
            
        Returns:
            Parsed response of output_schema type
        """
        # Get context
        context = self.get_context(client_id, question)
        
        system_prompt = self.chain_config.system_prompt_template
        if context:
            system_prompt += f"\n\n[参照コンテキスト]\n{context}"
        if additional_context:
            system_prompt += f"\n\n[追加情報]\n{additional_context}"
        
        try:
            completion = client.beta.chat.completions.parse(
                model=self.chain_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                response_format=output_schema
            )
            
            return completion.choices[0].message.parsed
            
        except Exception as e:
            logger.error(f"Structured query error: {e}")
            raise
    
    # ==========================================
    # Batch Operations
    # ==========================================
    
    def index_multiple_documents(
        self,
        client_id: str,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Index multiple documents.
        
        Args:
            client_id: Client UUID
            documents: List of {content, source_type, source_name, metadata}
            progress_callback: Optional callback(current, total)
            
        Returns:
            Summary of indexing results
        """
        results = {
            "total": len(documents),
            "success": 0,
            "failed": 0,
            "total_chunks": 0,
            "errors": []
        }
        
        for i, doc in enumerate(documents):
            try:
                result = self.index_document(
                    client_id=client_id,
                    content=doc["content"],
                    source_type=doc.get("source_type", "text"),
                    source_name=doc["source_name"],
                    metadata=doc.get("metadata")
                )
                
                if result.success:
                    results["success"] += 1
                    results["total_chunks"] += result.chunks_created
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "source": doc["source_name"],
                        "error": result.error
                    })
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "source": doc.get("source_name", "unknown"),
                    "error": str(e)
                })
            
            if progress_callback:
                progress_callback(i + 1, len(documents))
        
        return results


# ==========================================
# Singleton Instance
# ==========================================

_rag_service: Optional[RAGService] = None

def get_rag_service() -> RAGService:
    """Get singleton RAGService instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


# ==========================================
# Convenience Functions
# ==========================================

def rag_query(client_id: str, question: str) -> RAGResponse:
    """
    Quick RAG query function.
    
    Example:
        response = rag_query("client-123", "売上の傾向は？")
        print(response.answer)
    """
    return get_rag_service().query(client_id, question)


def rag_index(client_id: str, content: str, source_name: str) -> IndexingResult:
    """
    Quick document indexing function.
    
    Example:
        result = rag_index("client-123", "文書内容...", "report.txt")
    """
    return get_rag_service().index_document(
        client_id=client_id,
        content=content,
        source_type="text",
        source_name=source_name
    )
