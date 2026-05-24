-- Execution Store Migration to Supabase
-- Phase K: Data Persistence Consolidation
-- Date: 2026-02-08

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- TABLE: execution_actions
-- Stores action items for PDCA execution layer
-- =============================================
CREATE TABLE IF NOT EXISTS execution_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    objective TEXT,
    owner TEXT,
    due_date DATE,
    status TEXT DEFAULT 'Not Started' CHECK (status IN ('Not Started', 'In Progress', 'Done', 'Delayed')),
    priority TEXT DEFAULT 'Medium' CHECK (priority IN ('High', 'Medium', 'Low')),
    impact INTEGER DEFAULT 3 CHECK (impact >= 1 AND impact <= 5),
    effort INTEGER DEFAULT 3 CHECK (effort >= 1 AND effort <= 5),
    tags TEXT[] DEFAULT '{}',
    notes TEXT,
    strategy_run_id UUID REFERENCES strategy_runs(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID
);

-- Index for client queries
CREATE INDEX idx_execution_actions_client ON execution_actions(client_id);
CREATE INDEX idx_execution_actions_status ON execution_actions(status);

-- =============================================
-- TABLE: execution_kpis
-- Stores KPI definitions for monitoring
-- =============================================
CREATE TABLE IF NOT EXISTS execution_kpis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    definition TEXT,
    unit TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID
);

-- Index for client queries
CREATE INDEX idx_execution_kpis_client ON execution_kpis(client_id);

-- =============================================
-- TABLE: execution_kpi_values
-- Stores KPI targets and actuals
-- =============================================
CREATE TABLE IF NOT EXISTS execution_kpi_values (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kpi_id UUID NOT NULL REFERENCES execution_kpis(id) ON DELETE CASCADE,
    year_month TEXT NOT NULL, -- Format: YYYY-MM
    target_value NUMERIC,
    actual_value NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(kpi_id, year_month)
);

-- Index for KPI queries
CREATE INDEX idx_execution_kpi_values_kpi ON execution_kpi_values(kpi_id);
CREATE INDEX idx_execution_kpi_values_month ON execution_kpi_values(year_month);

-- =============================================
-- TABLE: execution_reviews
-- Stores monthly review records
-- =============================================
CREATE TABLE IF NOT EXISTS execution_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    year_month TEXT NOT NULL, -- Format: YYYY-MM
    kpi_gaps_json JSONB DEFAULT '{}',
    alerts TEXT[] DEFAULT '{}',
    summary TEXT,
    updated_hypotheses TEXT[] DEFAULT '{}',
    suggested_actions TEXT[] DEFAULT '{}',
    raw_llm_response_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    UNIQUE(client_id, year_month)
);

-- Index for client queries
CREATE INDEX idx_execution_reviews_client ON execution_reviews(client_id);
CREATE INDEX idx_execution_reviews_month ON execution_reviews(year_month);

-- =============================================
-- Enable Row Level Security
-- =============================================
ALTER TABLE execution_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_kpis ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_kpi_values ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_reviews ENABLE ROW LEVEL SECURITY;

-- RLS Policies (Allow authenticated users full access - refine as needed)
CREATE POLICY "execution_actions_policy" ON execution_actions 
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "execution_kpis_policy" ON execution_kpis 
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "execution_kpi_values_policy" ON execution_kpi_values 
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "execution_reviews_policy" ON execution_reviews 
    FOR ALL USING (auth.role() = 'authenticated');

-- =============================================
-- Update Trigger for updated_at
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_execution_actions_updated_at
    BEFORE UPDATE ON execution_actions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_execution_kpis_updated_at
    BEFORE UPDATE ON execution_kpis
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_execution_kpi_values_updated_at
    BEFORE UPDATE ON execution_kpi_values
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
