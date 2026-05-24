-- Create strategic_guardrails table
CREATE TABLE IF NOT EXISTS strategic_guardrails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL,
    mission_objective TEXT NOT NULL,
    time_horizon_years INT NOT NULL DEFAULT 3,
    investment_limit NUMERIC,
    risk_tolerance TEXT CHECK (risk_tolerance IN ('low', 'medium', 'high')),
    strategic_boundaries_json JSONB DEFAULT '{}'::jsonb, -- e.g. { "no_entry_markets": [], "excluded_models": [] }
    success_state_definition TEXT,
    decision_rules_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookup by client
CREATE INDEX IF NOT EXISTS idx_strategic_guardrails_client_id ON strategic_guardrails(client_id);
