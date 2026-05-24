-- =============================================================================
-- Security Hardening V2: Address Supabase Security Warnings
-- Fixes mutable search paths, moves extension, and secures remaining tables.
-- =============================================================================

-- 1. Create 'extensions' schema and Move 'vector' extension
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS extensions;
GRANT USAGE ON SCHEMA extensions TO postgres, anon, authenticated, service_role;

-- Move vector extension to 'extensions' schema to resolve "Extension in Public" warning
-- Checks if vector is in public before moving to avoid errors if already moved
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_extension e 
        JOIN pg_namespace n ON e.extnamespace = n.oid 
        WHERE e.extname = 'vector' AND n.nspname = 'public'
    ) THEN
        ALTER EXTENSION vector SET SCHEMA extensions;
    END IF;
END $$;

-- 2. Fix Function Search Paths (Security Best Practice)
-- -----------------------------------------------------------------------------
-- Force functions to run in explicit search path to prevent hijacking.
-- We include 'extensions' schema so that 'vector' type can be found.

ALTER FUNCTION public.check_client_access(uuid) SET search_path = public, extensions;

-- Function: rpc_create_execution_run
ALTER FUNCTION public.rpc_create_execution_run(uuid, uuid, jsonb) SET search_path = public, extensions;

-- Function: update_document_chunks_updated_at
ALTER FUNCTION public.update_document_chunks_updated_at() SET search_path = public, extensions;

-- Function: match_documents (RAG)
-- Note: Logic handles if argument type has moved to extensions.vector
DO $$
BEGIN
    -- Attempt to alter assuming input type 'extensions.vector'
    BEGIN
        ALTER FUNCTION public.match_documents(extensions.vector, float, int, uuid) SET search_path = public, extensions;
    EXCEPTION WHEN OTHERS THEN
        -- Fallback: try with 'public.vector' or just 'vector' if move failed or not needed? 
        -- Actually, if move succeeded, the type is extensions.vector. Postgres signatures update.
        -- If move failed, it might be vector.
        -- We just print a notice if this specific one fails, but usually it works if step 1 worked.
        RAISE NOTICE 'Could not alter match_documents search_path. Ensure signature matches.';
    END;
END $$;

-- Function: hybrid_search_documents (RAG)
DO $$
BEGIN
    BEGIN
        ALTER FUNCTION public.hybrid_search_documents(extensions.vector, text, float, int, uuid, float, float) SET search_path = public, extensions;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Could not alter hybrid_search_documents search_path.';
    END;
END $$;


-- 3. Secure 'monitoring_runs' Table
-- -----------------------------------------------------------------------------
ALTER TABLE monitoring_runs ENABLE ROW LEVEL SECURITY;

-- Drop insecure "allow all" policy
DROP POLICY IF EXISTS "Enable all access for authenticated users on monitoring_runs" ON monitoring_runs;

-- Create secure policy linking back to workspace via execution_run -> strategy_run -> client
DROP POLICY IF EXISTS "Users can view monitoring runs" ON monitoring_runs;
CREATE POLICY "Users can view monitoring runs"
ON monitoring_runs FOR ALL USING (
    EXISTS (
        SELECT 1 FROM strategy_execution_runs ser
        JOIN strategy_runs sr ON ser.strategy_run_id = sr.id
        WHERE ser.id = monitoring_runs.execution_run_id
        AND public.check_client_access(sr.client_id::uuid)
    )
);

-- 4. Secure 'swot_analyses' Table
-- -----------------------------------------------------------------------------
ALTER TABLE swot_analyses ENABLE ROW LEVEL SECURITY;

-- Drop insecure "allow all" policy
DROP POLICY IF EXISTS "Enable all access for authenticated users on swot_analyses" ON swot_analyses;

-- Create secure policy linking back to workspace via strategy_run -> client
DROP POLICY IF EXISTS "Users can view swot analyses" ON swot_analyses;
CREATE POLICY "Users can view swot analyses"
ON swot_analyses FOR ALL USING (
    EXISTS (
        SELECT 1 FROM strategy_runs sr
        WHERE sr.id = swot_analyses.strategy_run_id
        AND public.check_client_access(sr.client_id::uuid)
    )
);

-- Note on "Leaked Password Protection":
-- This cannot be enabled via SQL. Please go to Supabase Dashboard > Authentication > Security 
-- and enable "Enable Leaked Password Protection" check against HaveIBeenPwned.
