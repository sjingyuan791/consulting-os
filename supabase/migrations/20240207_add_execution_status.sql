-- Migration: Add Execution Status and Enhance RPC for Async Processing

-- 1. Add Status Columns
alter table strategy_execution_runs 
add column if not exists status text default 'COMPLETED'; -- PENDING, PROCESSING, COMPLETED, FAILED

alter table strategy_execution_runs 
add column if not exists error_message text;

-- 2. Update RPC to handle status and error_message
-- We recreate the function with the new columns mapped from the payload
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
    -- NOTE: In async flow, if it's PENDING, we still return the ID so the UI can poll it.
    if v_existing_id is not null then
        return v_existing_id;
    end if;

    -- B. Unset previous 'is_current' flags
    -- We Only do this if we are inserting a new one.
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
        coalesce(p_payload->>'status', 'PENDING'), -- Default to PENDING if provided, or logic elsewhere
        p_payload->>'error_message'
    ) returning id into v_new_id;
    
    return v_new_id;
end;
$$;
