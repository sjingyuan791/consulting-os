-- Consolidated Migration for Strategy Decisions & Execution
-- This file combines:
-- 1. Table Creation (Decisions & Execution Runs)
-- 2. Reliability Enhancements (Idempotency, Lineage)
-- 3. Async Status Extensions

-- SECTION 1: Base Tables
-- -----------------------------------------------------------------------------
-- Strategy Decisions Table
create table if not exists strategy_decisions (
  id uuid primary key default gen_random_uuid(),
  strategy_run_id uuid references strategy_runs(id),
  selected_option_id text,
  modified_parameters_json jsonb,
  rejected_options_json jsonb,
  decided_by uuid,
  decided_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index if not exists idx_strategy_decisions_run 
  on strategy_decisions(strategy_run_id);

-- Strategy Execution Runs Table
create table if not exists strategy_execution_runs (
  id uuid primary key default gen_random_uuid(),
  strategy_run_id uuid references strategy_runs(id),
  decision_id uuid references strategy_decisions(id),
  selected_option_snapshot_json jsonb, 
  execution_roadmap_json jsonb,
  financial_simulation_json jsonb,
  meta_json jsonb,
  created_by uuid,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  is_current boolean default true
);

create index if not exists idx_strategy_execution_runs_run 
  on strategy_execution_runs(strategy_run_id);

create index if not exists idx_strategy_execution_runs_current 
  on strategy_execution_runs(strategy_run_id) 
  where is_current = true;


-- SECTION 2: Reliability Enhancements & Lineage
-- -----------------------------------------------------------------------------
alter table strategy_execution_runs 
add column if not exists dataset_version_set_json jsonb;

alter table strategy_execution_runs 
add column if not exists module_version_hash text;

alter table strategy_execution_runs 
add column if not exists idempotency_key text;

create unique index if not exists idx_strategy_execution_idempotency 
on strategy_execution_runs(strategy_run_id, decision_id);


-- SECTION 3: Async Status Extensions
-- -----------------------------------------------------------------------------
alter table strategy_execution_runs 
add column if not exists status text default 'COMPLETED'; -- PENDING, PROCESSING, COMPLETED, FAILED

alter table strategy_execution_runs 
add column if not exists error_message text;


-- SECTION 4: Atomic RPC Function (Final Version)
-- -----------------------------------------------------------------------------
create or replace function rpc_create_execution_run(
    p_strategy_run_id uuid,
    p_decision_id uuid,
    p_payload jsonb
) 
returns uuid 
language plpgsql 
as $$
declare
    v_existing_id uuid;
    v_new_id uuid;
begin
    -- A. Idempotency Check
    select id into v_existing_id 
    from strategy_execution_runs 
    where strategy_run_id = p_strategy_run_id 
      and decision_id = p_decision_id
    limit 1;
    
    -- If it exists, we return it. 
    if v_existing_id is not null then
        return v_existing_id;
    end if;

    -- B. Unset previous 'is_current' flags
    update strategy_execution_runs 
    set is_current = false 
    where strategy_run_id = p_strategy_run_id 
      and is_current = true;
      
    -- C. Insert new record
    insert into strategy_execution_runs (
        strategy_run_id,
        decision_id,
        selected_option_snapshot_json,
        execution_roadmap_json,
        financial_simulation_json,
        dataset_version_set_json,
        module_version_hash,
        meta_json,
        is_current,
        created_by,
        status,
        error_message
    ) values (
        p_strategy_run_id,
        p_decision_id,
        p_payload->'selected_option_snapshot_json',
        p_payload->'execution_roadmap_json',
        p_payload->'financial_simulation_json',
        p_payload->'dataset_version_set_json',
        p_payload->>'module_version_hash',
        p_payload->'meta_json',
        true,
        (p_payload->>'created_by')::uuid,
        coalesce(p_payload->>'status', 'PENDING'),
        p_payload->>'error_message'
    ) returning id into v_new_id;
    
    return v_new_id;
end;
$$;
