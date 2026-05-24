-- Fix strategic_guardrails client_id type
-- Previously defined as UUID, but we use string identifiers (e.g. "demo-client")

ALTER TABLE strategic_guardrails ALTER COLUMN client_id TYPE TEXT;
