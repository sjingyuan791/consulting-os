-- Migration: Run Lifecycle Architecture (v2)

-- 1. Clients (Upgrade existing or create new)
-- Assuming 'clients' exists, adding columns. If not, create it.
create table if not exists clients (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  industry text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

alter table clients add column if not exists workspace_id uuid;
alter table clients add column if not exists region text;

-- 2. Datasets (Core entity, separate from versions)
create table if not exists datasets (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(id),
  dataset_type text not null, -- 'financial', 'internal', 'external'
  description text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. Dataset Versions (The immutable data snapshots)
create table if not exists dataset_versions (
  id uuid primary key default gen_random_uuid(),
  dataset_id uuid references datasets(id),
  version int not null,
  is_current boolean default true,
  source_type text, -- 'upload', 'api', 'manual'
  raw_storage_path text,
  normalized_json jsonb,
  quality_json jsonb,
  schema_hash text,
  created_by uuid, -- user_id if valid
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Index for fast lookup of current version
create index if not exists idx_dataset_versions_current 
  on dataset_versions(dataset_id) 
  where is_current = true;

-- 4. Analysis Runs (The 'Compute' record)
create table if not exists analysis_runs (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(id),
  dataset_version_set jsonb, -- { "financial": uuid, "internal": uuid }
  pipeline_version text,
  financial_metrics_json jsonb,
  sales_metrics_json jsonb,
  external_intelligence_json jsonb,
  internal_capability_json jsonb,
  created_by uuid,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 5. Strategy Runs (The 'Decision' record)
create table if not exists strategy_runs (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(id),
  analysis_run_id uuid references analysis_runs(id),
  guardrails_json jsonb,
  final_strategy_package_json jsonb,
  decision_log_json jsonb,
  meta_json jsonb,
  created_by uuid,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  is_current boolean default true
);

-- 6. Strategy Chat Logic
create table if not exists strategy_chat_threads (
  id uuid primary key default gen_random_uuid(),
  strategy_run_id uuid references strategy_runs(id),
  title text,
  created_by uuid,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists strategy_chat_messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid references strategy_chat_threads(id),
  role text, -- 'user', 'assistant', 'system'
  content jsonb,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);
