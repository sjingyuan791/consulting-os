-- Fix hybrid_search_documents return type mismatch
-- text_rank (real) vs double precision mismatch
-- Also ensures vector type usage is correct with extensions schema

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
SET search_path = public, extensions
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
            -- vector distance returns double precision usually, but let's be safe
            (1 - (dc.embedding <=> query_embedding))::float8 AS vec_sim
        FROM document_chunks dc
        WHERE 
            (filter_client_id IS NULL OR dc.client_id = filter_client_id)
            AND dc.embedding IS NOT NULL
            AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ),
    text_results AS (
        SELECT 
            dc.id,
            -- ts_rank returns real (float4), must cast to float8
            ts_rank(to_tsvector('simple', dc.content), plainto_tsquery('simple', query_text))::float8 AS txt_rank
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
        COALESCE(tr.txt_rank, 0.0)::float8 AS text_rank,
        (vr.vec_sim * vector_weight + COALESCE(tr.txt_rank, 0.0) * text_weight)::float8 AS combined_score
    FROM vector_results vr
    LEFT JOIN text_results tr ON vr.id = tr.id
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION hybrid_search_documents IS 'RAG: ハイブリッド検索（ベクトル＋全文）Fixed types';
