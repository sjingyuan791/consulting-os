-- Migration: Strategy Learning Engine
-- Capture effectiveness of strategy runs and generate next-cycle hypotheses.

create table if not exists strategy_learning_records (
    id uuid primary key default gen_random_uuid(),
    strategy_run_id uuid references strategy_runs(id),
    execution_run_id uuid references strategy_execution_runs(id),
    monitoring_run_id uuid references monitoring_runs(id),
    
    -- Performance Metrics
    effectiveness_score numeric, -- normalized score (e.g., 0.0 to 1.0 or -1.0 to 1.0)
    kpi_delta_json jsonb default '{}'::jsonb, -- comparative performance vs previous run
    evaluation_context_json jsonb default '{}'::jsonb, -- metadata about the evaluation
    
    -- Output
    generated_hypotheses_json jsonb default '[]'::jsonb, -- Potential next strategic moves
    
    -- Lineage
    lineage_json jsonb default '{}'::jsonb,
    dataset_version_set_json jsonb default '{}'::jsonb,
    module_version_hash text,
    
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Indexes for fast retrieval
create index if not exists idx_strategy_learning_run on strategy_learning_records(strategy_run_id);
create index if not exists idx_strategy_learning_exec on strategy_learning_records(execution_run_id);

-- RLS
alter table strategy_learning_records enable row level security;

create policy "Enable read access for authenticated users"
on strategy_learning_records for select
to authenticated
using (true);

create policy "Enable insert access for authenticated users"
on strategy_learning_records for insert
to authenticated
with check (true);
