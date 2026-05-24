"""
RAG Retriever - Document Search and Retrieval with Hybrid Search and Reranking.
Enhanced version with caching, multiple search strategies, and context optimization.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import time

from openai import OpenAI
from core.supabase_client import get_supabase_client
from core.config import Config

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=Config.OPENAI_API_KEY)


class SearchStrategy(str, Enum):
    """Available search strategies."""
    VECTOR = "vector"        # Pure vector similarity search
    HYBRID = "hybrid"        # Vector + Full-text search
    KEYWORD = "keyword"      # Pure keyword search (fallback)


@dataclass
class SearchConfig:
    """Configuration for document search."""
    strategy: SearchStrategy = SearchStrategy.HYBRID
    match_threshold: float = 0.3
    match_count: int = 5
    vector_weight: float = 0.7
    text_weight: float = 0.3
    enable_reranking: bool = True
    enable_cache: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes


@dataclass
class SearchResult:
    """Single search result."""
    id: str
    content: str
    similarity: float
    source_name: str
    source_type: str
    metadata: Dict[str, Any]


@dataclass
class RetrievalResult:
    """Complete retrieval result."""
    results: List[SearchResult]
    query: str
    strategy_used: SearchStrategy
    total_chunks_searched: int
    search_time_ms: float


class RAGRetriever:
    """
    Enhanced RAG Retriever with hybrid search, reranking, and caching.
    """
    
    EMBEDDING_MODEL = "text-embedding-3-small"
    RERANK_MODEL = "gpt-4o-mini"  # For reranking
    
    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self.supabase = get_supabase_client()
        self._cache: Dict[str, Tuple[float, RetrievalResult]] = {}
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for query text.
        """
        text = text.replace("\n", " ").strip()
        if not text:
            return []
            
        response = client.embeddings.create(
            input=[text],
            model=self.EMBEDDING_MODEL
        )
        return response.data[0].embedding
    
    def _get_cache_key(self, query: str, client_id: str) -> str:
        """Generate cache key for a query."""
        return hashlib.md5(f"{query}:{client_id}".encode()).hexdigest()
    
    def _get_cached(self, cache_key: str) -> Optional[RetrievalResult]:
        """Get cached result if still valid."""
        if not self.config.enable_cache:
            return None
            
        if cache_key in self._cache:
            timestamp, result = self._cache[cache_key]
            if time.time() - timestamp < self.config.cache_ttl_seconds:
                return result
            else:
                del self._cache[cache_key]
        return None
    
    def _set_cached(self, cache_key: str, result: RetrievalResult):
        """Cache a result."""
        if self.config.enable_cache:
            self._cache[cache_key] = (time.time(), result)
    
    def search_vector(
        self,
        query: str,
        client_id: str,
        match_threshold: Optional[float] = None,
        match_count: Optional[int] = None
    ) -> List[Dict]:
        """
        Pure vector similarity search.
        """
        query_embedding = self.generate_embedding(query)
        if not query_embedding:
            return []
        
        params = {
            "query_embedding": query_embedding,
            "match_threshold": match_threshold or self.config.match_threshold,
            "match_count": match_count or self.config.match_count,
            "filter_client_id": client_id
        }
        
        response = self.supabase.rpc("match_documents", params).execute()
        return response.data or []
    
    def search_hybrid(
        self,
        query: str,
        client_id: str,
        match_threshold: Optional[float] = None,
        match_count: Optional[int] = None
    ) -> List[Dict]:
        """
        Hybrid search combining vector similarity and full-text search.
        """
        query_embedding = self.generate_embedding(query)
        if not query_embedding:
            return []
        
        params = {
            "query_embedding": query_embedding,
            "query_text": query,
            "match_threshold": match_threshold or self.config.match_threshold,
            "match_count": match_count or self.config.match_count,
            "filter_client_id": client_id,
            "vector_weight": self.config.vector_weight,
            "text_weight": self.config.text_weight
        }
        
        try:
            response = self.supabase.rpc("hybrid_search_documents", params).execute()
            return response.data or []
        except Exception as e:
            logger.warning(f"Hybrid search failed, falling back to vector: {e}")
            return self.search_vector(query, client_id, match_threshold, match_count)
    
    def rerank_results(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Rerank results using LLM for better relevance.
        Only used when more results than needed are retrieved.
        """
        if len(results) <= top_k:
            return results
        
        # Build reranking prompt
        prompt = f"""Query: {query}

Rank the following document excerpts by relevance to the query.
Return a JSON array of indices in order of relevance (most relevant first).
Only include the top {top_k} most relevant.

Documents:
"""
        for i, doc in enumerate(results):
            content = doc.get("content", "")[:500]  # Limit content length
            prompt += f"\n[{i}] {content}\n"
        
        prompt += f"\nReturn only a JSON array like: [2, 0, 4, 1, 3]"
        
        try:
            response = client.chat.completions.create(
                model=self.RERANK_MODEL,
                messages=[
                    {"role": "system", "content": "You are a relevance ranking assistant. Return only valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            import json
            ranking_response = response.choices[0].message.content
            # Parse the response - handle both array and object formats
            parsed = json.loads(ranking_response)
            if isinstance(parsed, dict):
                indices = parsed.get("ranking", parsed.get("indices", list(range(top_k))))
            else:
                indices = parsed
            
            # Reorder results
            reranked = []
            for idx in indices[:top_k]:
                if 0 <= idx < len(results):
                    reranked.append(results[idx])
            
            return reranked
            
        except Exception as e:
            logger.warning(f"Reranking failed, using original order: {e}")
            return results[:top_k]
    
    def search(
        self,
        query: str,
        client_id: str,
        strategy: Optional[SearchStrategy] = None,
        match_count: Optional[int] = None
    ) -> RetrievalResult:
        """
        Main search method with automatic strategy selection.
        
        Args:
            query: Search query
            client_id: Client UUID
            strategy: Override default strategy
            match_count: Override default match count
            
        Returns:
            RetrievalResult with ranked documents
        """
        start_time = time.time()
        
        # Check cache
        cache_key = self._get_cache_key(query, client_id)
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # Determine strategy
        use_strategy = strategy or self.config.strategy
        count = match_count or self.config.match_count
        
        # Fetch more results if reranking is enabled
        fetch_count = count * 2 if self.config.enable_reranking else count
        
        # Execute search
        if use_strategy == SearchStrategy.HYBRID:
            raw_results = self.search_hybrid(query, client_id, match_count=fetch_count)
        else:
            raw_results = self.search_vector(query, client_id, match_count=fetch_count)
        
        # Rerank if enabled and we have results
        if self.config.enable_reranking and len(raw_results) > count:
            raw_results = self.rerank_results(query, raw_results, top_k=count)
        else:
            raw_results = raw_results[:count]
        
        # Convert to SearchResult objects
        search_results = []
        for r in raw_results:
            search_results.append(SearchResult(
                id=r.get("id", ""),
                content=r.get("content", ""),
                similarity=r.get("similarity", r.get("combined_score", 0)),
                source_name=r.get("source_name", "unknown"),
                source_type=r.get("source_type", "unknown"),
                metadata=r.get("metadata", {})
            ))
        
        search_time = (time.time() - start_time) * 1000
        
        result = RetrievalResult(
            results=search_results,
            query=query,
            strategy_used=use_strategy,
            total_chunks_searched=len(raw_results),
            search_time_ms=search_time
        )
        
        # Cache result
        self._set_cached(cache_key, result)
        
        return result
    
    def retrieve_context(
        self,
        query: str,
        client_id: str,
        max_tokens: int = 3000,
        include_sources: bool = True
    ) -> str:
        """
        High-level function to get context string for LLM.
        Optimizes context length for token limits.
        
        Args:
            query: User query
            client_id: Client UUID
            max_tokens: Approximate max tokens for context
            include_sources: Whether to include source citations
            
        Returns:
            Formatted context string
        """
        result = self.search(query, client_id)
        
        if not result.results:
            return ""
        
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough char to token ratio
        
        for i, doc in enumerate(result.results):
            content = doc.content
            
            # Truncate if needed
            if total_chars + len(content) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 200:
                    content = content[:remaining] + "..."
                else:
                    break
            
            if include_sources:
                source_info = f"[Source: {doc.source_name} | Relevance: {doc.similarity:.2f}]"
                context_parts.append(f"{source_info}\n{content}")
            else:
                context_parts.append(content)
            
            total_chars += len(content)
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_sources_for_response(
        self,
        query: str,
        client_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get source citations for a response.
        
        Returns:
            List of source information for citations
        """
        result = self.search(query, client_id, match_count=3)
        
        sources = []
        for doc in result.results:
            sources.append({
                "source": doc.source_name,
                "type": doc.source_type,
                "relevance": round(doc.similarity, 2),
                "excerpt": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
            })
        
        return sources


# ==========================================
# Convenience Functions (Backwards Compatibility)
# ==========================================

def generate_embedding(text: str) -> List[float]:
    """Legacy function for backwards compatibility."""
    retriever = RAGRetriever()
    return retriever.generate_embedding(text)


def search_documents(
    query: str,
    client_id: str,
    match_threshold: float = 0.5,
    match_count: int = 5
) -> List[Dict]:
    """Legacy function for backwards compatibility."""
    retriever = RAGRetriever(SearchConfig(match_threshold=match_threshold))
    result = retriever.search(query, client_id, match_count=match_count)
    
    # Convert to legacy format
    return [
        {
            "id": r.id,
            "content": r.content,
            "metadata": r.metadata,
            "similarity": r.similarity
        }
        for r in result.results
    ]


def retrieve_context(query: str, client_id: str) -> str:
    """Legacy function for backwards compatibility."""
    retriever = RAGRetriever()
    return retriever.retrieve_context(query, client_id)
