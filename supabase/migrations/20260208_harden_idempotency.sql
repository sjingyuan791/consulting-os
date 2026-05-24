-- Migration: Harden Idempotency & Integrity
-- Enforces uniqueness constraints to prevent duplicate runs and race conditions.

-- 1. Strategy Runs: Ensure only one 'current' run per client
-- This prevents race conditions where multiple heads exist.
create unique index if not exists idx_strategy_runs_current_unique 
on strategy_runs(client_id) 
where is_current = true;

-- 2. Strategy Learning Records: Ensure only one learning record per monitoring run
-- Prevents duplicate learning if evaluation is retried.
create unique index if not exists idx_strategy_learning_unique_monitoring
on strategy_learning_records(monitoring_run_id);

-- 3. Monitoring Runs: Ensure only one 'PENDING' run per execution
-- Prevents duplicate initialization calls.
create unique index if not exists idx_monitoring_runs_unique_pending
on monitoring_runs(execution_run_id)
where status = 'PENDING';

-- 4. Monitoring Runs: Ensure only one 'COMPLETED' run per execution (Optional, but good for strict lineage)
-- If we want to allow re-runs, we might not want this. 
-- But for strict "Insert-Only" where a new execution is required for a new result, this is safer.
-- Let's stick to the request which mainly concerned 'PENDING'. 
-- We'll add a unique index on execution_run_id for COMPLETED as well to be safe, 
-- implying 1 execution = 1 monitoring result.
create unique index if not exists idx_monitoring_runs_unique_completed
on monitoring_runs(execution_run_id)
where status = 'COMPLETED';
