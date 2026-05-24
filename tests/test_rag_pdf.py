import pytest
from unittest.mock import MagicMock, patch, mock_open
import sys
from core.rag_indexer import RAGIndexer, SourceType, IndexingResult
import io

# Mock pypdf if not installed, though we confirmed it is
try:
    import pypdf
except ImportError:
    pypdf = MagicMock()

@pytest.fixture
def mock_supabase():
    with patch("core.rag_indexer.get_supabase_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def mock_openai():
    with patch("core.rag_indexer.client") as mock:
        yield mock

def test_index_pdf_success(mock_supabase, mock_openai):
    """Test successful PDF indexing."""
    indexer = RAGIndexer()
    
    # Mock PDF reader
    with patch("pypdf.PdfReader") as mock_reader_cls:
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock(), MagicMock()]
        mock_reader.pages[0].extract_text.return_value = "Page 1 content."
        mock_reader.pages[1].extract_text.return_value = "Page 2 content."
        mock_reader_cls.return_value = mock_reader
        
        # Mock embeddings
        mock_openai.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536)
        ]
        
        # Mock insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [1, 2]
        
        # Call index_pdf with bytes
        pdf_bytes = b"%PDF-1.4..."
        result = indexer.index_pdf("client-123", pdf_bytes, "test.pdf")
        
        # Verify
        assert result.success is True
        assert result.chunks_created == 2
        
        # Verify text accumulation
        # The exact content assertion depends on splitting, but we know it extracted text
        mock_reader.pages[0].extract_text.assert_called_once()

def test_index_pdf_empty(mock_supabase, mock_openai):
    """Test PDF with no entries."""
    indexer = RAGIndexer()
    
    with patch("pypdf.PdfReader") as mock_reader_cls:
        mock_reader = MagicMock()
        mock_reader.pages = [] # No pages
        mock_reader_cls.return_value = mock_reader
        
        result = indexer.index_pdf("client-123", b"empty", "empty.pdf")
        
        assert result.success is False
        assert result.error == "Could not extract text from PDF (empty)"

def test_index_pdf_file_path(mock_supabase, mock_openai):
    """Test PDF indexing with file path."""
    indexer = RAGIndexer()
    
    with patch("pypdf.PdfReader") as mock_reader_cls:
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()]
        mock_reader.pages[0].extract_text.return_value = "Content"
        mock_reader_cls.return_value = mock_reader
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [1]
        mock_openai.embeddings.create.return_value.data = [MagicMock(embedding=[0.1]*1536)]
        
        result = indexer.index_pdf("client-123", "path/to/doc.pdf", "doc.pdf")
        
        assert result.success is True
        mock_reader_cls.assert_called_with("path/to/doc.pdf")
