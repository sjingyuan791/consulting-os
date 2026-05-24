-- Strategy Evolution Pipeline Tables
-- 7-Stage Consulting Reasoning Pipeline Infrastructure
-- Date: 2026-02-08

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- TABLE: pipeline_runs
-- Master record for each pipeline execution
-- =============================================
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'PENDING' CHECK (status IN (
        'PENDING', 'RUNNING', 'AWAITING_APPROVAL', 
        'COMPLETED', 'FAILED', 'CANCELLED'
    )),
    version INT NOT NULL DEFAULT 1,
    parent_run_id UUID REFERENCES pipeline_runs(id),
    current_stage INT DEFAULT 0,
    config_json JSONB DEFAULT '{}',
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID
);

-- Ensure unique version per client
CREATE UNIQUE INDEX idx_pipeline_runs_client_version 
    ON pipeline_runs(client_id, version);

-- =============================================
-- TABLE: stage_outputs
-- Stores input/output for each pipeline stage
-- =============================================
CREATE TABLE IF NOT EXISTS stage_outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    stage_number INT NOT NULL CHECK (stage_number BETWEEN 1 AND 7),
    stage_name TEXT NOT NULL,
    parent_stage_output_id UUID REFERENCES stage_outputs(id),
    
    -- Stage Data
    input_json JSONB NOT NULL DEFAULT '{}',
    output_json JSONB,
    
    -- Execution Metadata
    status TEXT DEFAULT 'PENDING' CHECK (status IN (
        'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED'
    )),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    execution_time_ms INT,
    
    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Additional Metadata
    metadata_json JSONB DEFAULT '{}',
    
    UNIQUE(pipeline_run_id, stage_number)
);

-- Stage name reference
COMMENT ON COLUMN stage_outputs.stage_name IS 
    'Stage 1: ROA Deductive Engine, Stage 2: Root Cause Inductive Engine, 
     Stage 3: Hypothesis Verification Planner, Stage 4: Strategy Design Engine,
     Stage 5: HOW-Tree Tactical Generator, Stage 6: KPI & Financial Planning,
     Stage 7: Mid-Term Plan Generator';

-- =============================================
-- TABLE: human_checkpoints
-- Human-in-the-loop approval records
-- =============================================
CREATE TABLE IF NOT EXISTS human_checkpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stage_output_id UUID NOT NULL REFERENCES stage_outputs(id) ON DELETE CASCADE,
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    
    -- Checkpoint Details
    checkpoint_type TEXT NOT NULL CHECK (checkpoint_type IN (
        'root_cause_confirmation',
        'strategy_direction',
        'tactical_prioritization'
    )),
    checkpoint_name TEXT NOT NULL,
    
    -- Decision
    status TEXT DEFAULT 'PENDING' CHECK (status IN (
        'PENDING', 'APPROVED', 'REJECTED', 'REVISION_REQUESTED'
    )),
    approved_by UUID,
    decision TEXT,
    rationale TEXT,
    decided_at TIMESTAMPTZ,
    
    -- Feedback for revisions
    feedback_json JSONB DEFAULT '{}',
    revision_instructions TEXT,
    
    -- Notification tracking
    notification_sent_at TIMESTAMPTZ,
    reminder_count INT DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- TABLE: mid_term_plans
-- Generated management plan documents
-- =============================================
CREATE TABLE IF NOT EXISTS mid_term_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Versioning
    version INT NOT NULL DEFAULT 1,
    plan_period TEXT NOT NULL, -- e.g., "2026-2030"
    
    -- Plan Content (complete JSON document)
    plan_content_json JSONB NOT NULL,
    
    -- Workflow Status
    status TEXT DEFAULT 'DRAFT' CHECK (status IN (
        'DRAFT', 'REVIEW', 'APPROVED', 'PUBLISHED', 'ARCHIVED'
    )),
    
    -- Approval
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    
    -- Export tracking
    exported_formats TEXT[] DEFAULT '{}', -- ['pdf', 'docx', 'pptx']
    last_exported_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(client_id, version)
);

-- =============================================
-- TABLE: roa_analysis_cache
-- Cached financial analysis results
-- =============================================
CREATE TABLE IF NOT EXISTS roa_analysis_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    stage_output_id UUID REFERENCES stage_outputs(id),
    
    -- ROA Breakdown
    analysis_year INT NOT NULL,
    roa NUMERIC(10, 4),
    roe NUMERIC(10, 4),
    profit_margin NUMERIC(10, 4),
    asset_turnover NUMERIC(10, 4),
    financial_leverage NUMERIC(10, 4),
    
    -- Sub-metrics
    gross_margin NUMERIC(10, 4),
    operating_margin NUMERIC(10, 4),
    net_margin NUMERIC(10, 4),
    receivables_turnover NUMERIC(10, 4),
    inventory_turnover NUMERIC(10, 4),
    fixed_asset_turnover NUMERIC(10, 4),
    
    -- Identified Issues
    weak_nodes_json JSONB DEFAULT '[]',
    hypotheses_json JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(client_id, analysis_year)
);

-- =============================================
-- TABLE: causal_maps
-- Stored causal relationship graphs
-- =============================================
CREATE TABLE IF NOT EXISTS causal_maps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    stage_output_id UUID REFERENCES stage_outputs(id),
    
    -- Graph Structure
    nodes_json JSONB NOT NULL DEFAULT '[]',
    edges_json JSONB NOT NULL DEFAULT '[]',
    
    -- Identified Causes
    primary_root_cause_json JSONB,
    secondary_causes_json JSONB DEFAULT '[]',
    
    -- Graph Metadata
    node_count INT,
    edge_count INT,
    max_depth INT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- Indexes for Performance
-- =============================================
CREATE INDEX idx_pipeline_runs_client ON pipeline_runs(client_id);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_stage_outputs_run ON stage_outputs(pipeline_run_id);
CREATE INDEX idx_stage_outputs_stage ON stage_outputs(stage_number);
CREATE INDEX idx_checkpoints_status ON human_checkpoints(status);
CREATE INDEX idx_checkpoints_run ON human_checkpoints(pipeline_run_id);
CREATE INDEX idx_mid_term_plans_client ON mid_term_plans(client_id);
CREATE INDEX idx_mid_term_plans_status ON mid_term_plans(status);

-- =============================================
-- Row Level Security
-- =============================================
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE stage_outputs ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE mid_term_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE roa_analysis_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE causal_maps ENABLE ROW LEVEL SECURITY;

-- Policies (authenticated users)
CREATE POLICY "pipeline_runs_policy" ON pipeline_runs 
    FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "stage_outputs_policy" ON stage_outputs 
    FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "human_checkpoints_policy" ON human_checkpoints 
    FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "mid_term_plans_policy" ON mid_term_plans 
    FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "roa_analysis_cache_policy" ON roa_analysis_cache 
    FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "causal_maps_policy" ON causal_maps 
    FOR ALL USING (auth.role() = 'authenticated');

-- =============================================
-- Updated At Triggers
-- =============================================
CREATE TRIGGER trigger_mid_term_plans_updated_at
    BEFORE UPDATE ON mid_term_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- Helper Functions
-- =============================================

-- Get next pipeline version for client
CREATE OR REPLACE FUNCTION get_next_pipeline_version(p_client_id UUID)
RETURNS INT AS $$
    SELECT COALESCE(MAX(version), 0) + 1 
    FROM pipeline_runs 
    WHERE client_id = p_client_id;
$$ LANGUAGE SQL;

-- Get current stage for a pipeline run
CREATE OR REPLACE FUNCTION get_pipeline_current_stage(p_run_id UUID)
RETURNS INT AS $$
    SELECT COALESCE(MAX(stage_number), 0)
    FROM stage_outputs
    WHERE pipeline_run_id = p_run_id
    AND status = 'COMPLETED';
$$ LANGUAGE SQL;
