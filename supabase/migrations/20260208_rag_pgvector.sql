-- RAG: pgvector Extension and Document Chunks
-- Supabase pgvector setup for RAG (Retrieval-Augmented Generation)

-- ============================================
-- 1. Enable pgvector extension
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 2. Document Chunks Table
-- ============================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Content
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI text-embedding-3-small dimensions
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    source_type TEXT CHECK (source_type IN ('csv', 'pdf', 'text', 'manual', 'system')),
    source_name TEXT,
    chunk_index INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comment
COMMENT ON TABLE document_chunks IS 'RAG: ドキュメントチャンクとベクトル埋め込み';
COMMENT ON COLUMN document_chunks.embedding IS '1536次元のOpenAI埋め込みベクトル';
COMMENT ON COLUMN document_chunks.source_type IS 'ドキュメントソースタイプ: csv, pdf, text, manual, system';

-- ============================================
-- 3. Indexes
-- ============================================

-- Vector similarity search index (IVFFlat for large datasets)
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
    ON document_chunks 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Client filtering index
CREATE INDEX IF NOT EXISTS idx_document_chunks_client_id 
    ON document_chunks(client_id);

-- Source type filtering
CREATE INDEX IF NOT EXISTS idx_document_chunks_source_type 
    ON document_chunks(source_type);

-- Full-text search index for hybrid search
CREATE INDEX IF NOT EXISTS idx_document_chunks_content_fts 
    ON document_chunks 
    USING gin(to_tsvector('simple', content));

-- ============================================
-- 4. RLS Policies
-- ============================================
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- Authenticated users can view all documents (simplified policy)
CREATE POLICY "Authenticated users can view documents"
    ON document_chunks FOR SELECT
    TO authenticated
    USING (true);

-- Authenticated users can insert documents
CREATE POLICY "Authenticated users can insert documents"
    ON document_chunks FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Authenticated users can update their documents
CREATE POLICY "Authenticated users can update documents"
    ON document_chunks FOR UPDATE
    TO authenticated
    USING (true);

-- Authenticated users can delete documents
CREATE POLICY "Authenticated users can delete documents"
    ON document_chunks FOR DELETE
    TO authenticated
    USING (true);

-- ============================================
-- 5. Vector Search RPC Function
-- ============================================
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 5,
    filter_client_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    client_id uuid,
    content text,
    metadata jsonb,
    source_type text,
    source_name text,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id,
        dc.client_id,
        dc.content,
        dc.metadata,
        dc.source_type,
        dc.source_name,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE 
        (filter_client_id IS NULL OR dc.client_id = filter_client_id)
        AND dc.embedding IS NOT NULL
        AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_documents IS 'RAG: ベクトル類似度検索';

-- ============================================
-- 6. Hybrid Search RPC Function (Vector + Full-text)
-- ============================================
CREATE OR REPLACE FUNCTION hybrid_search_documents(
    query_embedding vector(1536),
    query_text text,
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 10,
    filter_client_id uuid DEFAULT NULL,
    vector_weight float DEFAULT 0.7,
    text_weight float DEFAULT 0.3
)
RETURNS TABLE (
    id uuid,
    client_id uuid,
    content text,
    metadata jsonb,
    source_type text,
    source_name text,
    vector_similarity float,
    text_rank float,
    combined_score float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        SELECT 
            dc.id,
            dc.client_id,
            dc.content,
            dc.metadata,
            dc.source_type,
            dc.source_name,
            1 - (dc.embedding <=> query_embedding) AS vec_sim
        FROM document_chunks dc
        WHERE 
            (filter_client_id IS NULL OR dc.client_id = filter_client_id)
            AND dc.embedding IS NOT NULL
            AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ),
    text_results AS (
        SELECT 
            dc.id,
            ts_rank(to_tsvector('simple', dc.content), plainto_tsquery('simple', query_text)) AS txt_rank
        FROM document_chunks dc
        WHERE 
            (filter_client_id IS NULL OR dc.client_id = filter_client_id)
            AND to_tsvector('simple', dc.content) @@ plainto_tsquery('simple', query_text)
    )
    SELECT 
        vr.id,
        vr.client_id,
        vr.content,
        vr.metadata,
        vr.source_type,
        vr.source_name,
        vr.vec_sim AS vector_similarity,
        COALESCE(tr.txt_rank, 0) AS text_rank,
        (vr.vec_sim * vector_weight + COALESCE(tr.txt_rank, 0) * text_weight) AS combined_score
    FROM vector_results vr
    LEFT JOIN text_results tr ON vr.id = tr.id
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION hybrid_search_documents IS 'RAG: ハイブリッド検索（ベクトル＋全文）';

-- ============================================
-- 7. Utility Functions
-- ============================================

-- Get document count by client
CREATE OR REPLACE FUNCTION get_document_chunk_count(p_client_id uuid)
RETURNS integer
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT COUNT(*)::integer 
    FROM document_chunks 
    WHERE client_id = p_client_id;
$$;

-- Delete all chunks for a client
CREATE OR REPLACE FUNCTION delete_client_documents(p_client_id uuid)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    deleted_count integer;
BEGIN
    DELETE FROM document_chunks 
    WHERE client_id = p_client_id;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- ============================================
-- 8. Updated_at Trigger
-- ============================================
CREATE OR REPLACE FUNCTION update_document_chunks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_document_chunks_updated_at
    BEFORE UPDATE ON document_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_document_chunks_updated_at();
