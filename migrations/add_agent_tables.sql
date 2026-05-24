-- ============================================================
-- Migration: OpenAI Agents SDK integration tables
-- Run in Supabase SQL Editor
-- ============================================================

-- agent_steps: one row per SDK agent execution (全監査ログ)
CREATE TABLE IF NOT EXISTS agent_steps (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id uuid REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    stage_number int,
    stage_name text,
    agent_name text NOT NULL,
    tool_calls_json jsonb DEFAULT '[]',
    output_json jsonb,
    validations_json jsonb DEFAULT '[]',
    created_at timestamptz DEFAULT now()
);

ALTER TABLE agent_steps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view agent_steps in their workspace"
    ON agent_steps FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM pipeline_runs pr
            JOIN clients c ON pr.client_id = c.id
            JOIN workspaces w ON c.workspace_id = w.id
            WHERE pr.id = agent_steps.pipeline_run_id
            AND w.owner_user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can insert agent_steps"
    ON agent_steps FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pipeline_runs pr
            JOIN clients c ON pr.client_id = c.id
            JOIN workspaces w ON c.workspace_id = w.id
            WHERE pr.id = agent_steps.pipeline_run_id
            AND w.owner_user_id = auth.uid()
        )
    );

CREATE INDEX IF NOT EXISTS idx_agent_steps_pipeline_run ON agent_steps(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_agent_steps_agent_name ON agent_steps(agent_name);


-- evidence: claim provenance tracking per pipeline run
CREATE TABLE IF NOT EXISTS evidence (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id uuid REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    claim_id text NOT NULL,
    source_type text CHECK (source_type IN (
        'financial_data', 'market_data', 'interview', 'calculated', 'inferred'
    )),
    source_ref text,      -- e.g. "financials.2024.sales"
    snippet_hash text,    -- SHA256 of evidence snippet for dedup
    created_at timestamptz DEFAULT now()
);

ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view evidence in their workspace"
    ON evidence FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM pipeline_runs pr
            JOIN clients c ON pr.client_id = c.id
            JOIN workspaces w ON c.workspace_id = w.id
            WHERE pr.id = evidence.pipeline_run_id
            AND w.owner_user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can insert evidence"
    ON evidence FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pipeline_runs pr
            JOIN clients c ON pr.client_id = c.id
            JOIN workspaces w ON c.workspace_id = w.id
            WHERE pr.id = evidence.pipeline_run_id
            AND w.owner_user_id = auth.uid()
        )
    );

CREATE INDEX IF NOT EXISTS idx_evidence_pipeline_run ON evidence(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_evidence_claim ON evidence(claim_id);
