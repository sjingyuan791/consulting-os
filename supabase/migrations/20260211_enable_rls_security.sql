-- =============================================================================
-- Enable Row Level Security (RLS) for All Tables
-- Fixes "RLS Policy Warnings" in Supabase
-- =============================================================================

-- 1. Helper Function: Check Workspace Access
-- -----------------------------------------------------------------------------
-- Returns true if the current user owns the workspace associated with the client
CREATE OR REPLACE FUNCTION public.check_client_access(client_uuid uuid)
RETURNS boolean AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM clients c
    JOIN workspaces w ON c.workspace_id = w.id
    WHERE c.id = client_uuid
      AND w.owner_user_id = auth.uid()
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Workspaces
-- -----------------------------------------------------------------------------
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own workspace" ON workspaces;
CREATE POLICY "Users can view their own workspace"
ON workspaces FOR SELECT USING (auth.uid() = owner_user_id);

DROP POLICY IF EXISTS "Users can insert their own workspace" ON workspaces;
CREATE POLICY "Users can insert their own workspace"
ON workspaces FOR INSERT WITH CHECK (auth.uid() = owner_user_id);

DROP POLICY IF EXISTS "Users can update their own workspace" ON workspaces;
CREATE POLICY "Users can update their own workspace"
ON workspaces FOR UPDATE USING (auth.uid() = owner_user_id);

-- 3. Clients
-- -----------------------------------------------------------------------------
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view clients in their workspace" ON clients;
CREATE POLICY "Users can view clients in their workspace"
ON clients FOR ALL USING (
    EXISTS (
        SELECT 1 FROM workspaces
        WHERE id = clients.workspace_id
        AND owner_user_id = auth.uid()
    )
);

-- 4. Datasets & Versions
-- -----------------------------------------------------------------------------
ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view datasets" ON datasets;
CREATE POLICY "Users can view datasets"
ON datasets FOR ALL USING (public.check_client_access(client_id::uuid));

ALTER TABLE dataset_versions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view dataset versions" ON dataset_versions;
CREATE POLICY "Users can view dataset versions"
ON dataset_versions FOR ALL USING (
    EXISTS (
        SELECT 1 FROM datasets
        WHERE id = dataset_versions.dataset_id
        AND public.check_client_access(datasets.client_id::uuid)
    )
);

-- 5. Data Categories (Public/Shared)
-- -----------------------------------------------------------------------------
ALTER TABLE data_categories ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Everyone can read categories" ON data_categories;
CREATE POLICY "Everyone can read categories"
ON data_categories FOR SELECT USING (auth.role() = 'authenticated');

ALTER TABLE dataset_types ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Everyone can read types" ON dataset_types;
CREATE POLICY "Everyone can read types"
ON dataset_types FOR SELECT USING (auth.role() = 'authenticated');

-- 6. Strategy Tables (Runs, Decisions, Execution)
-- -----------------------------------------------------------------------------
ALTER TABLE strategy_runs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view strategy runs" ON strategy_runs;
CREATE POLICY "Users can view strategy runs"
ON strategy_runs FOR ALL USING (public.check_client_access(client_id::uuid));

ALTER TABLE strategy_decisions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view decisions" ON strategy_decisions;
CREATE POLICY "Users can view decisions"
ON strategy_decisions FOR ALL USING (
    EXISTS (
        SELECT 1 FROM strategy_runs
        WHERE id = strategy_decisions.strategy_run_id
        AND public.check_client_access(strategy_runs.client_id::uuid)
    )
);

ALTER TABLE strategy_execution_runs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view execution runs" ON strategy_execution_runs;
CREATE POLICY "Users can view execution runs"
ON strategy_execution_runs FOR ALL USING (
    EXISTS (
        SELECT 1 FROM strategy_runs
        WHERE id = strategy_execution_runs.strategy_run_id
        AND public.check_client_access(strategy_runs.client_id::uuid)
    )
);

-- 7. Chat Tables
-- -----------------------------------------------------------------------------
ALTER TABLE strategy_chat_threads ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view threads" ON strategy_chat_threads;
CREATE POLICY "Users can view threads"
ON strategy_chat_threads FOR ALL USING (
    EXISTS (
        SELECT 1 FROM strategy_runs
        WHERE id = strategy_chat_threads.strategy_run_id
        AND public.check_client_access(strategy_runs.client_id::uuid)
    )
);

ALTER TABLE strategy_chat_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view messages" ON strategy_chat_messages;
CREATE POLICY "Users can view messages"
ON strategy_chat_messages FOR ALL USING (
    EXISTS (
        SELECT 1 FROM strategy_chat_threads t
        JOIN strategy_runs s ON t.strategy_run_id = s.id
        WHERE t.id = strategy_chat_messages.thread_id
        AND public.check_client_access(s.client_id::uuid)
    )
);

-- 8. Mid-term Plan Documents
-- -----------------------------------------------------------------------------
ALTER TABLE midterm_plan_documents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view midterm plans" ON midterm_plan_documents;
-- client_id is TEXT here, cast ensures compatibility
CREATE POLICY "Users can view midterm plans"
ON midterm_plan_documents FOR ALL USING (
    public.check_client_access(client_id::uuid)
);

-- 9. Strategic Guardrails
-- -----------------------------------------------------------------------------
ALTER TABLE strategic_guardrails ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view guardrails" ON strategic_guardrails;
CREATE POLICY "Users can view guardrails"
ON strategic_guardrails FOR ALL USING (public.check_client_access(client_id::uuid));

-- 10. Document Chunks (RAG)
-- -----------------------------------------------------------------------------
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Authenticated users can view documents" ON document_chunks;
DROP POLICY IF EXISTS "Authenticated users can insert documents" ON document_chunks;
DROP POLICY IF EXISTS "Authenticated users can update documents" ON document_chunks;
DROP POLICY IF EXISTS "Authenticated users can delete documents" ON document_chunks;
DROP POLICY IF EXISTS "Users can access document chunks" ON document_chunks;

CREATE POLICY "Users can access document chunks"
ON document_chunks FOR ALL USING (public.check_client_access(client_id::uuid));

-- 11. Client Data Tables (Legacy/Alternative)
-- -----------------------------------------------------------------------------
ALTER TABLE client_datasets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view client_datasets" ON client_datasets;
CREATE POLICY "Users can view client_datasets"
ON client_datasets FOR ALL USING (public.check_client_access(client_id::uuid));

ALTER TABLE client_analysis_runs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view client_analysis_runs" ON client_analysis_runs;
CREATE POLICY "Users can view client_analysis_runs"
ON client_analysis_runs FOR ALL USING (public.check_client_access(client_id::uuid));

-- 12. Cleanup
-- -----------------------------------------------------------------------------
ALTER TABLE analysis_runs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can access analysis runs" ON analysis_runs;
CREATE POLICY "Users can access analysis runs"
ON analysis_runs FOR ALL USING (public.check_client_access(client_id::uuid));
