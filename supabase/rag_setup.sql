-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- Create a table to store document chunks
create table if not exists document_chunks (
  id bigserial primary key,
  client_id uuid not null, -- Foreign key to Clients table if exists, or just uuid
  -- foreign key (client_id) references clients(id), -- Uncomment if strict Relation needed
  
  content text, -- The actual text chunk
  metadata jsonb, -- Extra data (filename, page number, etc)
  embedding vector(1536) -- OpenAI text-embedding-3-small dimensions
);

-- Create a function to search for documents
create or replace function match_documents (
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter_client_id uuid
) returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    document_chunks.id,
    document_chunks.content,
    document_chunks.metadata,
    1 - (document_chunks.embedding <=> query_embedding) as similarity
  from document_chunks
  where 1 - (document_chunks.embedding <=> query_embedding) > match_threshold
  and document_chunks.client_id = filter_client_id
  order by document_chunks.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Create an index for faster queries (IVFFlat is good for large datasets, HNSW is better but more memory)
-- For MVP, standard index or HNSW
create index on document_chunks using hnsw (embedding vector_cosine_ops);
