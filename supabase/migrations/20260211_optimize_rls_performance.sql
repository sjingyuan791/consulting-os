-- =============================================================================
-- Security Hardening V3: Performance Optimization & Cleanup
-- Addresses warnings about "re-evaluating current_setting()", duplicates, and permissive policies.
-- =============================================================================

-- 1. Workspaces: Cleanup Duplicates & Optimize
-- -----------------------------------------------------------------------------
-- First, drop ALL potential variations of conflicting policies
DROP POLICY IF EXISTS "Users can view their own workspace" ON workspaces;
DROP POLICY IF EXISTS "Users can view their own workspaces" ON workspaces; -- Plural variant

DROP POLICY IF EXISTS "Users can insert their own workspace" ON workspaces;
DROP POLICY IF EXISTS "Users can insert their own workspaces" ON workspaces;

DROP POLICY IF EXISTS "Users can update their own workspace" ON workspaces;
DROP POLICY IF EXISTS "Users can update their own workspaces" ON workspaces;

-- Re-create optimized policies
-- Optimization: wrapping auth.uid() in (select ... ) allows Postgres to cache the result for the statement.
-- Restriction: explicit 'TO authenticated' prevents 'anon' warnings.

CREATE POLICY "Users can view their own workspace"
ON workspaces FOR SELECT TO authenticated
USING ((select auth.uid()) = owner_user_id);

CREATE POLICY "Users can insert their own workspace"
ON workspaces FOR INSERT TO authenticated
WITH CHECK ((select auth.uid()) = owner_user_id);

CREATE POLICY "Users can update their own workspace"
ON workspaces FOR UPDATE TO authenticated
USING ((select auth.uid()) = owner_user_id);


-- 2. Clients: Optimize
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view clients in their workspace" ON clients;

CREATE POLICY "Users can view clients in their workspace"
ON clients FOR ALL TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM workspaces
        WHERE id = clients.workspace_id
        AND owner_user_id = (select auth.uid())
    )
);


-- 3. Data Categories & Types: Optimize auth.role()
-- -----------------------------------------------------------------------------
-- Optimize data_categories
DROP POLICY IF EXISTS "Everyone can read categories" ON data_categories;

CREATE POLICY "Everyone can read categories"
ON data_categories FOR SELECT TO authenticated
USING ((select auth.role()) = 'authenticated'); -- Optimized

-- Optimize dataset_types
DROP POLICY IF EXISTS "Everyone can read types" ON dataset_types;

CREATE POLICY "Everyone can read types"
ON dataset_types FOR SELECT TO authenticated
USING ((select auth.role()) = 'authenticated');


-- 4. Check Client Access Function Helper (Optional but recommended)
-- -----------------------------------------------------------------------------
-- We can also optimize the helper function associated with RLS if needed, 
-- but since it's SECURITY DEFINER, the impact is different. 
-- However, we can perform a quick no-op check to ensure it's robust.
-- (No changes to function needed for this specific warning, as warnings were on policies)
