-- =============================================================================
-- Data Integrity Check (Pre-Migration Validation)
-- Purpose: Verify that data is clean before adding constraints or changing types.
-- Run this BEFORE running the schema improvement script.
-- =============================================================================

-- 1. Check for Invalid UUIDs in 'strategic_guardrails'
--    Changing from TEXT to UUID will fail if invalid formats exist.
-- -----------------------------------------------------------------------------
SELECT id, client_id, 'Invalid UUID Format' as issue
FROM strategic_guardrails
WHERE client_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- 2. Check for Orphaned Records (Referential Integrity)
--    Adding Foreign Keys will fail if child records point to non-existent parents.
-- -----------------------------------------------------------------------------

-- Check orphaned strategic_guardrails
SELECT sg.id, sg.client_id, 'Orphaned Guardrail' as issue
FROM strategic_guardrails sg
LEFT JOIN clients c ON sg.client_id::uuid = c.id
WHERE c.id IS NULL;

-- Check orphaned midterm_plan_documents
SELECT mp.id, mp.client_id, 'Orphaned Midterm Plan' as issue
FROM midterm_plan_documents mp
LEFT JOIN clients c ON mp.client_id::uuid = c.id
WHERE c.id IS NULL;

-- Check orphaned client_datasets
SELECT cd.dataset_id, cd.client_id, 'Orphaned Dataset' as issue
FROM client_datasets cd
LEFT JOIN clients c ON cd.client_id = c.id
WHERE c.id IS NULL AND cd.client_id IS NOT NULL;


-- If this script returns NO rows, it is safe to proceed with the migration.
-- If rows are returned, those records must be fixed or deleted first.
