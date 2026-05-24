"""
RAG Indexer - Document Chunking and Embedding Generation.
Enhanced version with batch processing, multiple file formats, and progress tracking.
"""
import os
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import hashlib
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from core.supabase_client import get_supabase_client
from core.config import Config

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=Config.OPENAI_API_KEY)


class SourceType(str, Enum):
    """Document source types."""
    CSV = "csv"
    PDF = "pdf"
    TEXT = "text"
    MANUAL = "manual"
    SYSTEM = "system"


@dataclass
class ChunkingConfig:
    """Configuration for text chunking."""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separators: List[str] = None
    
    def __post_init__(self):
        if self.separators is None:
            # Japanese-optimized separators
            self.separators = ["\n\n", "\n", "。", ".", " ", ""]


@dataclass
class IndexingResult:
    """Result of document indexing operation."""
    success: bool
    chunks_created: int
    document_id: Optional[str] = None
    error: Optional[str] = None


class RAGIndexer:
    """
    Enhanced RAG Indexer with batch processing and multiple format support.
    """
    
    # Embedding model configuration
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536
    MAX_BATCH_SIZE = 100  # OpenAI batch limit
    
    def __init__(self, chunking_config: Optional[ChunkingConfig] = None):
        self.config = chunking_config or ChunkingConfig()
        self.supabase = get_supabase_client()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=self.config.separators
        )
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks using configured splitter.
        
        Args:
            text: Raw text to split
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        return self._splitter.split_text(text)
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text chunk.
        
        Args:
            text: Text to embed
            
        Returns:
            1536-dimensional embedding vector
        """
        text = text.replace("\n", " ").strip()
        if not text:
            return [0.0] * self.EMBEDDING_DIMENSIONS
            
        response = client.embeddings.create(
            input=[text],
            model=self.EMBEDDING_MODEL
        )
        return response.data[0].embedding
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch (more efficient).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Clean texts
        cleaned = [t.replace("\n", " ").strip() for t in texts]
        
        # Process in batches
        all_embeddings = []
        for i in range(0, len(cleaned), self.MAX_BATCH_SIZE):
            batch = cleaned[i:i + self.MAX_BATCH_SIZE]
            
            # Skip empty texts
            valid_batch = [t if t else "empty" for t in batch]
            
            response = client.embeddings.create(
                input=valid_batch,
                model=self.EMBEDDING_MODEL
            )
            
            batch_embeddings = [d.embedding for d in response.data]
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    def index_document(
        self,
        client_id: str,
        content: str,
        source_type: SourceType,
        source_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> IndexingResult:
        """
        Index a document: chunk, embed, and store.
        
        Args:
            client_id: Client UUID
            content: Document content
            source_type: Type of source document
            source_name: Name/path of source document
            metadata: Additional metadata
            progress_callback: Optional callback(current, total) for progress
            
        Returns:
            IndexingResult with success status and chunk count
        """
        try:
            # 1. Chunk the content
            chunks = self.chunk_text(content)
            if not chunks:
                return IndexingResult(
                    success=False,
                    chunks_created=0,
                    error="No content to index"
                )
            
            total_chunks = len(chunks)
            logger.info(f"Indexing {total_chunks} chunks for client {client_id}")
            
            # 2. Generate embeddings in batch
            embeddings = self.generate_embeddings_batch(chunks)
            
            # 3. Prepare records
            base_metadata = metadata or {}
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            records = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                records.append({
                    "client_id": client_id,
                    "content": chunk,
                    "embedding": embedding,
                    "source_type": source_type.value,
                    "source_name": source_name,
                    "chunk_index": i,
                    "metadata": {
                        **base_metadata,
                        "chunk_index": i,
                        "total_chunks": total_chunks,
                        "content_hash": content_hash
                    }
                })
                
                if progress_callback:
                    progress_callback(i + 1, total_chunks)
            
            # 4. Batch insert
            result = self.supabase.table("document_chunks").insert(records).execute()
            
            if result.data:
                logger.info(f"Successfully indexed {len(result.data)} chunks")
                return IndexingResult(
                    success=True,
                    chunks_created=len(result.data),
                    document_id=content_hash
                )
            else:
                return IndexingResult(
                    success=False,
                    chunks_created=0,
                    error="Insert returned no data"
                )
                
        except Exception as e:
            logger.error(f"Indexing error: {type(e).__name__}: {e}")
            return IndexingResult(
                success=False,
                chunks_created=0,
                error=str(e)
            )
    
    def index_csv_content(
        self,
        client_id: str,
        csv_content: str,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IndexingResult:
        """
        Index CSV content with row-aware chunking.
        """
        return self.index_document(
            client_id=client_id,
            content=csv_content,
            source_type=SourceType.CSV,
            source_name=filename,
            metadata={"format": "csv", **(metadata or {})}
        )
    
    def index_text_content(
        self,
        client_id: str,
        text_content: str,
        title: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IndexingResult:
        """
        Index plain text content.
        """
        return self.index_document(
            client_id=client_id,
            content=text_content,
            source_type=SourceType.TEXT,
            source_name=title,
            metadata=metadata
        )
        
    def index_pdf(
        self,
        client_id: str,
        pdf_file: Any,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IndexingResult:
        """
        Index PDF file content.
        
        Args:
            client_id: Client UUID
            pdf_file: File object or path to PDF
            filename: Original filename
            metadata: Additional metadata
        """
        try:
            import pypdf
            import io
            
            # Handle file path or file object
            if isinstance(pdf_file, str):
                reader = pypdf.PdfReader(pdf_file)
            else:
                # Assume bytes or file-like object
                if isinstance(pdf_file, bytes):
                    pdf_file = io.BytesIO(pdf_file)
                reader = pypdf.PdfReader(pdf_file)
                
            text_content = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n\n"
            
            if not text_content.strip():
                return IndexingResult(
                    success=False,
                    chunks_created=0,
                    error="Could not extract text from PDF (empty)"
                )
                
            return self.index_document(
                client_id=client_id,
                content=text_content,
                source_type=SourceType.PDF,
                source_name=filename,
                metadata={"format": "pdf", "pages": len(reader.pages), **(metadata or {})}
            )
            
        except ImportError:
            return IndexingResult(
                success=False,
                chunks_created=0,
                error="pypdf library not installed"
            )
        except Exception as e:
            logger.error(f"PDF indexing error: {e}")
            return IndexingResult(
                success=False,
                chunks_created=0,
                error=f"Failed to process PDF: {str(e)}"
            )
    
    def delete_document(self, client_id: str, source_name: str) -> int:
        """
        Delete all chunks for a specific document.
        
        Returns:
            Number of chunks deleted
        """
        try:
            result = self.supabase.table("document_chunks").delete().eq(
                "client_id", client_id
            ).eq(
                "source_name", source_name
            ).execute()
            
            deleted_count = len(result.data) if result.data else 0
            logger.info(f"Deleted {deleted_count} chunks for {source_name}")
            return deleted_count
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return 0
    
    def delete_all_client_documents(self, client_id: str) -> int:
        """
        Delete all documents for a client.
        
        Returns:
            Number of chunks deleted
        """
        try:
            result = self.supabase.rpc(
                "delete_client_documents",
                {"p_client_id": client_id}
            ).execute()
            
            return result.data if result.data else 0
        except Exception as e:
            logger.error(f"Delete all error: {e}")
            return 0
    
    def get_document_count(self, client_id: str) -> int:
        """
        Get total chunk count for a client.
        """
        try:
            result = self.supabase.rpc(
                "get_document_chunk_count",
                {"p_client_id": client_id}
            ).execute()
            return result.data if result.data else 0
        except Exception:
            return 0
    
    def list_indexed_documents(self, client_id: str) -> List[Dict[str, Any]]:
        """
        List all indexed documents for a client.
        
        Returns:
            List of {source_name, source_type, chunk_count, created_at}
        """
        try:
            result = self.supabase.table("document_chunks").select(
                "source_name, source_type, created_at"
            ).eq("client_id", client_id).execute()
            
            if not result.data:
                return []
            
            # Aggregate by source_name
            docs = {}
            for row in result.data:
                name = row["source_name"]
                if name not in docs:
                    docs[name] = {
                        "source_name": name,
                        "source_type": row["source_type"],
                        "chunk_count": 0,
                        "created_at": row["created_at"]
                    }
                docs[name]["chunk_count"] += 1
            
            return list(docs.values())
        except Exception as e:
            logger.error(f"List error: {e}")
            return []


# ==========================================
# Convenience Functions
# ==========================================

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Legacy function for backwards compatibility.
    Splits text into chunks using recursive character splitter.
    """
    indexer = RAGIndexer(ChunkingConfig(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    ))
    return indexer.chunk_text(text)


def generate_embedding(text: str) -> List[float]:
    """
    Legacy function for backwards compatibility.
    Generates embedding for a single text chunk.
    """
    indexer = RAGIndexer()
    return indexer.generate_embedding(text)


def index_document(client_id: str, content: str, metadata: Dict[str, Any]):
    """
    Legacy function for backwards compatibility.
    Chunks, embeds, and stores a document in Supabase.
    """
    indexer = RAGIndexer()
    result = indexer.index_document(
        client_id=client_id,
        content=content,
        source_type=SourceType.MANUAL,
        source_name=metadata.get("filename", "unknown"),
        metadata=metadata
    )
    
    if not result.success:
        raise Exception(result.error)
    
    print(f"Indexing complete. {result.chunks_created} chunks created.")
