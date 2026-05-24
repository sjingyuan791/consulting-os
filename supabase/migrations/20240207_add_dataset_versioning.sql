-- Migration: Add Versioning Support

-- 1. Add is_current to client_datasets
alter table client_datasets 
add column if not exists is_current boolean default true;

-- Ensure only one is_current per client/type (optional partial index, but for now simple is fine)
create index if not exists idx_client_datasets_current 
on client_datasets(client_id, dataset_type) 
where is_current = true;

-- 2. Add version tracking to analysis runs
alter table client_analysis_runs
add column if not exists dataset_version_financial int,
add column if not exists dataset_version_sales int;
