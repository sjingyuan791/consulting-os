-- Migration: Strategy Refinement Lineage
-- Enables strict versioning of strategy runs via parent pointers.

-- 1. Add Parent Pointer for Lineage
alter table strategy_runs 
add column if not exists parent_strategy_run_id uuid references strategy_runs(id);

-- 2. Add Refinement Context (Store what triggered this version)
alter table strategy_runs
add column if not exists refinement_context_json jsonb;

-- 3. Add Index for Lineage Traversal
create index if not exists idx_strategy_runs_parent 
on strategy_runs(parent_strategy_run_id);

-- 4. Add Status to Monitoring Runs (Pipeline Linkage)
alter table monitoring_runs
add column if not exists status text default 'COMPLETED'; -- PENDING, COMPLETED, FAILED

-- 5. Helper Function to Commit Refinement (Insert-Only)
create or replace function rpc_commit_strategy_refinement(
    p_client_id uuid,
    p_parent_run_id uuid,
    p_analysis_run_id uuid,
    p_package jsonb,
    p_refinement_context jsonb,
    p_created_by uuid
) 
returns uuid 
language plpgsql 
as $$
declare
    v_new_id uuid;
begin
    -- A. Unset previous 'is_current' flags for this client
    -- (We assume only one active strategy head per client for simplicity in this OS)
    update strategy_runs 
    set is_current = false 
    where client_id = p_client_id 
      and is_current = true;
      
    -- B. Insert New Version
    insert into strategy_runs (
        client_id,
        analysis_run_id,
        parent_strategy_run_id,
        final_strategy_package_json,
        refinement_context_json,
        meta_json,
        created_by,
        is_current,
        guardrails_json -- Inherit from package
    ) values (
        p_client_id,
        p_analysis_run_id,
        p_parent_run_id,
        p_package,
        p_refinement_context,
        p_package->'meta', -- Extract meta directly
        p_created_by,
        true,
        p_package->'guardrails'
    ) returning id into v_new_id;
    
    return v_new_id;
end;
$$;
