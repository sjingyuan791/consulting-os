-- Migration: Enhance Execution Reliability (Idempotency & Atomicity)

-- 1. Add new columns for lineage and idempotency
alter table strategy_execution_runs 
add column if not exists dataset_version_set_json jsonb;

alter table strategy_execution_runs 
add column if not exists module_version_hash text;

alter table strategy_execution_runs 
add column if not exists idempotency_key text;

-- 2. Add Unique Idempotency Constraint
-- Ensures only one execution run per (strategy_run, decision) combination
-- Use 'decision_id' as the effective idempotency key naturally, but adding explicit key is also good.
-- For now, we enforce uniqueness on the decision_id for a given run context.
create unique index if not exists idx_strategy_execution_idempotency 
on strategy_execution_runs(strategy_run_id, decision_id);


-- 3. RPC for Atomic Transaction
-- Supabase API execution is stateless. To ensure we unset previous 'is_current' flags
-- AND insert the new one in a single atomic transaction, we use a Postgres Function.

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
        created_by
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
        (p_payload->>'created_by')::uuid
    ) returning id into v_new_id;
    
    return v_new_id;
end;
$$;
