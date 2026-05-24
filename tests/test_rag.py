"""
Test RAG Components.
RAGインデクサー、リトリーバー、サービスのテスト
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestRAGIndexer:
    """RAGIndexer のテスト"""
    
    def test_chunk_text_basic(self):
        """基本的なテキストチャンク"""
        from core.rag_indexer import RAGIndexer, ChunkingConfig
        
        config = ChunkingConfig(chunk_size=100, chunk_overlap=20)
        indexer = RAGIndexer(config)
        
        text = "あ" * 250  # 250文字のテスト
        chunks = indexer.chunk_text(text)
        
        assert len(chunks) >= 2  # 100文字チャンクで2つ以上
    
    def test_chunk_text_empty(self):
        """空テキストのチャンク"""
        from core.rag_indexer import RAGIndexer
        
        indexer = RAGIndexer()
        chunks = indexer.chunk_text("")
        
        assert chunks == []
    
    def test_chunk_text_with_separators(self):
        """セパレータを使用したチャンク"""
        from core.rag_indexer import RAGIndexer, ChunkingConfig
        
        config = ChunkingConfig(chunk_size=50, chunk_overlap=10)
        indexer = RAGIndexer(config)
        
        text = "第一段落です。\n\n第二段落です。\n\n第三段落です。"
        chunks = indexer.chunk_text(text)
        
        assert len(chunks) >= 1
    
    def test_source_type_enum(self):
        """SourceType列挙型"""
        from core.rag_indexer import SourceType
        
        assert SourceType.CSV == "csv"
        assert SourceType.PDF == "pdf"
        assert SourceType.TEXT == "text"
        assert SourceType.MANUAL == "manual"
    
    def test_chunking_config_defaults(self):
        """ChunkingConfigデフォルト値"""
        from core.rag_indexer import ChunkingConfig
        
        config = ChunkingConfig()
        
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert "。" in config.separators
    
    def test_indexing_result_model(self):
        """IndexingResultモデル"""
        from core.rag_indexer import IndexingResult
        
        result = IndexingResult(
            success=True,
            chunks_created=5,
            document_id="doc-123"
        )
        
        assert result.success is True
        assert result.chunks_created == 5


class TestRAGRetriever:
    """RAGRetriever のテスト"""
    
    def test_search_config_defaults(self):
        """SearchConfigデフォルト値"""
        from core.rag_retriever import SearchConfig, SearchStrategy
        
        config = SearchConfig()
        
        assert config.strategy == SearchStrategy.HYBRID
        assert config.match_threshold == 0.3
        assert config.match_count == 5
        assert config.vector_weight == 0.7
        assert config.enable_cache is True
    
    def test_search_strategy_enum(self):
        """SearchStrategy列挙型"""
        from core.rag_retriever import SearchStrategy
        
        assert SearchStrategy.VECTOR == "vector"
        assert SearchStrategy.HYBRID == "hybrid"
        assert SearchStrategy.KEYWORD == "keyword"
    
    def test_search_result_model(self):
        """SearchResultモデル"""
        from core.rag_retriever import SearchResult
        
        result = SearchResult(
            id="chunk-001",
            content="テストコンテンツ",
            similarity=0.85,
            source_name="test.csv",
            source_type="csv",
            metadata={"test": True}
        )
        
        assert result.similarity == 0.85
        assert result.source_name == "test.csv"
    
    def test_retrieval_result_model(self):
        """RetrievalResultモデル"""
        from core.rag_retriever import RetrievalResult, SearchResult, SearchStrategy
        
        result = RetrievalResult(
            results=[
                SearchResult(
                    id="1",
                    content="test",
                    similarity=0.9,
                    source_name="doc.txt",
                    source_type="text",
                    metadata={}
                )
            ],
            query="テストクエリ",
            strategy_used=SearchStrategy.HYBRID,
            total_chunks_searched=10,
            search_time_ms=50.5
        )
        
        assert len(result.results) == 1
        assert result.search_time_ms == 50.5


class TestRAGService:
    """RAGService のテスト"""
    
    def test_citation_model(self):
        """Citationモデル"""
        from core.rag_service import Citation
        
        citation = Citation(
            source_name="report.pdf",
            source_type="pdf",
            relevance=0.92,
            excerpt="重要な情報..."
        )
        
        assert citation.source_name == "report.pdf"
        assert citation.relevance == 0.92
    
    def test_rag_response_model(self):
        """RAGResponseモデル"""
        from core.rag_service import RAGResponse, Citation
        
        response = RAGResponse(
            answer="回答テキスト",
            citations=[
                Citation(
                    source_name="doc.txt",
                    source_type="text",
                    relevance=0.85,
                    excerpt="引用..."
                )
            ],
            context_used=True,
            confidence_score=0.88,
            model_used="gpt-4o-mini"
        )
        
        assert response.context_used is True
        assert response.confidence_score == 0.88
        assert len(response.citations) == 1
    
    def test_rag_chain_config_defaults(self):
        """RAGChainConfigデフォルト値"""
        from core.rag_service import RAGChainConfig
        
        config = RAGChainConfig()
        
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.3
        assert config.include_citations is True
        assert config.context_max_tokens == 3000
    
    def test_rag_service_creation(self):
        """RAGServiceの作成"""
        with patch('core.rag_indexer.get_supabase_client'), \
             patch('core.rag_retriever.get_supabase_client'):
            from core.rag_service import RAGService
            
            service = RAGService()
            
            assert service is not None
            assert service.indexer is not None
            assert service.retriever is not None


class TestRAGIntegration:
    """RAG統合テスト"""
    
    def test_indexer_retriever_compatibility(self):
        """IndexerとRetrieverの互換性"""
        from core.rag_indexer import RAGIndexer, ChunkingConfig
        from core.rag_retriever import RAGRetriever, SearchConfig
        
        # 同じ埋め込みモデルを使用
        indexer = RAGIndexer()
        retriever = RAGRetriever()
        
        assert indexer.EMBEDDING_MODEL == retriever.EMBEDDING_MODEL
        assert indexer.EMBEDDING_DIMENSIONS == 1536
    
    def test_legacy_functions_exist(self):
        """下位互換性関数の存在確認"""
        from core.rag_indexer import chunk_text, generate_embedding, index_document
        from core.rag_retriever import search_documents, retrieve_context
        
        # 関数が存在する
        assert callable(chunk_text)
        assert callable(generate_embedding)
        assert callable(index_document)
        assert callable(search_documents)
        assert callable(retrieve_context)
    
    def test_convenience_functions_exist(self):
        """便利関数の存在確認"""
        from core.rag_service import rag_query, rag_index, get_rag_service
        
        assert callable(rag_query)
        assert callable(rag_index)
        assert callable(get_rag_service)


class TestChunkingStrategies:
    """チャンキング戦略のテスト"""
    
    def test_japanese_text_chunking(self):
        """日本語テキストのチャンク"""
        from core.rag_indexer import RAGIndexer, ChunkingConfig
        
        config = ChunkingConfig(chunk_size=50, chunk_overlap=10)
        indexer = RAGIndexer(config)
        
        text = "これは最初の文です。これは二番目の文です。これは三番目の文です。"
        chunks = indexer.chunk_text(text)
        
        # 句点で分割される
        assert len(chunks) >= 1
    
    def test_paragraph_chunking(self):
        """段落でのチャンク"""
        from core.rag_indexer import RAGIndexer, ChunkingConfig
        
        config = ChunkingConfig(chunk_size=100, chunk_overlap=20)
        indexer = RAGIndexer(config)
        
        text = "第一段落の内容です。\n\n第二段落の内容です。\n\n第三段落の内容です。"
        chunks = indexer.chunk_text(text)
        
        assert len(chunks) >= 1


class TestCachingBehavior:
    """キャッシュ動作のテスト"""
    
    def test_cache_key_generation(self):
        """キャッシュキー生成"""
        with patch('core.rag_retriever.get_supabase_client'):
            from core.rag_retriever import RAGRetriever
            
            retriever = RAGRetriever()
            
            key1 = retriever._get_cache_key("query1", "client1")
            key2 = retriever._get_cache_key("query1", "client2")
            key3 = retriever._get_cache_key("query1", "client1")
            
            assert key1 != key2  # 異なるクライアントは異なるキー
            assert key1 == key3  # 同じクエリとクライアントは同じキー
    
    def test_cache_disabled(self):
        """キャッシュ無効化"""
        from core.rag_retriever import SearchConfig
        
        config = SearchConfig(enable_cache=False)
        
        assert config.enable_cache is False
