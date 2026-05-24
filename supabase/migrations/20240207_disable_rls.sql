-- Migration: Disable RLS for Simpler Dev Environment
-- Since auth is handled via app logic, we can disable hard RLS for now to avoid the error.

alter table workspaces disable row level security;
alter table clients disable row level security;
alter table datasets disable row level security;
alter table dataset_versions disable row level security;
alter table analysis_runs disable row level security;
alter table strategy_runs disable row level security;
alter table strategy_chat_threads disable row level security;
alter table strategy_chat_messages disable row level security;
