-- Migration: Create Client Data Tables

-- 1. Clients Table (Master)
create table if not exists clients (
  client_id uuid primary key default gen_random_uuid(),
  workspace_id uuid, -- For future multi-tenancy (optional now)
  client_name text not null,
  industry text,
  created_at timestamp with time zone default now()
);

-- 2. Client Datasets (Raw Data)
create table if not exists client_datasets (
  dataset_id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(client_id) on delete cascade,
  dataset_type text not null, -- 'financials', 'sales'
  data_json jsonb, -- The normalized data
  quality_json jsonb, -- The quality gate result
  version int default 1,
  uploaded_at timestamp with time zone default now()
);

-- 3. Client Analysis Runs (Processed Insights)
create table if not exists client_analysis_runs (
  run_id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(client_id) on delete cascade,
  financial_metrics_json jsonb,
  sales_metrics_json jsonb,
  strategy_context_json jsonb,
  created_at timestamp with time zone default now()
);

-- Indexes for performance
create index if not exists idx_client_datasets_client_id on client_datasets(client_id);
create index if not exists idx_client_analysis_runs_client_id on client_analysis_runs(client_id);
