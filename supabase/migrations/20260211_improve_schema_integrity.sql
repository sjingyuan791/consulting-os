-- =============================================================================
-- Schema Improvement v2: Type Conversions & Foreign Keys (with Policy Handling)
-- Purpose: Enforce data integrity (UUID) and handle RLS dependencies.
-- =============================================================================

-- 0. PREPARATION: Drop dependent RLS policies
--    Postgres does not allow altering column type if it is used in a policy.
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view guardrails" ON strategic_guardrails;
DROP POLICY IF EXISTS "Users can view midterm plans" ON midterm_plan_documents;
DROP POLICY IF EXISTS "Users can view client_datasets" ON client_datasets;
DROP POLICY IF EXISTS "Users can view client_analysis_runs" ON client_analysis_runs;


-- 1. Fix 'strategic_guardrails' (TEXT -> UUID)
-- -----------------------------------------------------------------------------
ALTER TABLE strategic_guardrails
  ALTER COLUMN client_id TYPE UUID USING client_id::uuid;

ALTER TABLE strategic_guardrails
  ADD CONSTRAINT strategic_guardrails_client_id_fkey
  FOREIGN KEY (client_id) REFERENCES clients(id)
  ON DELETE CASCADE;

-- 2. Fix 'midterm_plan_documents' (TEXT/UUID integrity)
-- -----------------------------------------------------------------------------
ALTER TABLE midterm_plan_documents
  ALTER COLUMN client_id TYPE UUID USING client_id::uuid;

ALTER TABLE midterm_plan_documents
  ADD CONSTRAINT midterm_plan_documents_client_id_fkey
  FOREIGN KEY (client_id) REFERENCES clients(id)
  ON DELETE CASCADE;

-- 3. Add Missing Foreign Keys to other tables
-- -----------------------------------------------------------------------------

-- client_datasets
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'client_datasets_client_id_fkey'
    ) THEN
        ALTER TABLE client_datasets
        ADD CONSTRAINT client_datasets_client_id_fkey
        FOREIGN KEY (client_id) REFERENCES clients(id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- client_analysis_runs
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'client_analysis_runs_client_id_fkey'
    ) THEN
        ALTER TABLE client_analysis_runs
        ADD CONSTRAINT client_analysis_runs_client_id_fkey
        FOREIGN KEY (client_id) REFERENCES clients(id)
        ON DELETE CASCADE;
    END IF;
END $$;


-- 4. RESTORE: Re-create RLS Policies (Optimized without Casts)
--    Since client_id is now UUID, we typically don't need casting, 
--    but we keep `::uuid` just in case check_client_access signature expects specific type matching.
--    Actually, we can now pass it cleanly.
-- -----------------------------------------------------------------------------

-- Strategic Guardrails
CREATE POLICY "Users can view guardrails"
ON strategic_guardrails FOR ALL USING (public.check_client_access(client_id));

-- Midterm Plan Documents
CREATE POLICY "Users can view midterm plans"
ON midterm_plan_documents FOR ALL USING (public.check_client_access(client_id));

-- Client Datasets
CREATE POLICY "Users can view client_datasets"
ON client_datasets FOR ALL USING (public.check_client_access(client_id));

-- Client Analysis Runs
CREATE POLICY "Users can view client_analysis_runs"
ON client_analysis_runs FOR ALL USING (public.check_client_access(client_id));


-- 5. Optimization: Add Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_strategic_guardrails_client_id ON strategic_guardrails(client_id);
CREATE INDEX IF NOT EXISTS idx_midterm_plan_documents_client_id ON midterm_plan_documents(client_id);
CREATE INDEX IF NOT EXISTS idx_client_datasets_client_id ON client_datasets(client_id);
CREATE INDEX IF NOT EXISTS idx_client_analysis_runs_client_id ON client_analysis_runs(client_id);
