-- Migration: Strategy Decisions and Execution Runs (Human-in-the-Loop)

-- 1. Strategy Decisions Table
-- Records the human decision: which option was selected, what parameters were modified, etc.
create table if not exists strategy_decisions (
  id uuid primary key default gen_random_uuid(),
  strategy_run_id uuid references strategy_runs(id),
  selected_option_id text, -- ID from the strategy options list (e.g. 'opt_3')
  modified_parameters_json jsonb, -- { "investment": 50000, ... }
  rejected_options_json jsonb, -- { "opt_1": "Too risky", ... }
  decided_by uuid, -- User ID
  decided_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Index for lookup by strategy_run
create index if not exists idx_strategy_decisions_run 
  on strategy_decisions(strategy_run_id);


-- 2. Strategy Execution Runs Table
-- Records the COMPUTED outcome of a decision.
-- Stored separately to preserve the original strategy_run strategies (options) 
-- while allowing multiple "what-if" execution simulations.
create table if not exists strategy_execution_runs (
  id uuid primary key default gen_random_uuid(),
  strategy_run_id uuid references strategy_runs(id), -- Link back to original parent run
  decision_id uuid references strategy_decisions(id), -- Link to the specific decision
  
  -- The exact configuration used for this execution (merged original option + modifications)
  selected_option_snapshot_json jsonb, 
  
  -- The computed results
  execution_roadmap_json jsonb,
  financial_simulation_json jsonb,
  
  meta_json jsonb,
  created_by uuid,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  
  -- Versioning: only one execution run should be considered 'current' for a given strategy_run?
  -- Or maybe for a given decision? Usually for the strategy_run context.
  is_current boolean default true
);

-- Index for lookup
create index if not exists idx_strategy_execution_runs_run 
  on strategy_execution_runs(strategy_run_id);

create index if not exists idx_strategy_execution_runs_current 
  on strategy_execution_runs(strategy_run_id) 
  where is_current = true;
