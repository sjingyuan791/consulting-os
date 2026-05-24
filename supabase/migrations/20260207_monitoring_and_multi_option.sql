-- Migration: 20260207_monitoring_and_multi_option.sql
-- Description: Adds tables and columns for Multi-Option Strategy Decisions and Execution Monitoring

-- 1. Modify strategy_decisions to support multi-option selection
ALTER TABLE strategy_decisions
ADD COLUMN IF NOT EXISTS selected_options_json JSONB DEFAULT '[]'::jsonb, -- List of {option_id, weight, phase}
ADD COLUMN IF NOT EXISTS assumed_kpi_targets_json JSONB DEFAULT '{}'::jsonb, -- {year: {kpi_id: target}}
ADD COLUMN IF NOT EXISTS decision_rationale_json JSONB DEFAULT '{}'::jsonb; -- Context/Reasoning

-- 2. Modify strategy_execution_runs to track execution phase and lineage
ALTER TABLE strategy_execution_runs
ADD COLUMN IF NOT EXISTS assumed_kpi_targets_json JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS execution_phase INT DEFAULT 1,
ADD COLUMN IF NOT EXISTS decision_lineage_json JSONB DEFAULT '{}'::jsonb; -- {origin_chat_ids: [], dataset_versions: ...}

-- 3. Create monitoring_runs table
CREATE TABLE IF NOT EXISTS monitoring_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_run_id UUID REFERENCES strategy_execution_runs(id) ON DELETE CASCADE,
    kpi_actuals_json JSONB NOT NULL DEFAULT '{}'::jsonb, -- {year_month: {kpi_id: value}}
    gap_analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb, -- {gaps: [], recommended_actions: []}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);

-- 4. Create swot_analyses table (from Phase Definition)
CREATE TABLE IF NOT EXISTS swot_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_run_id UUID REFERENCES strategy_runs(id) ON DELETE CASCADE,
    swot_data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    cross_swot_data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);

-- Enable RLS for new tables
ALTER TABLE monitoring_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE swot_analyses ENABLE ROW LEVEL SECURITY;

-- Policies (Permissive for prototype)
CREATE POLICY "Enable all access for authenticated users on monitoring_runs"
ON monitoring_runs FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Enable all access for authenticated users on swot_analyses"
ON swot_analyses FOR ALL TO authenticated USING (true) WITH CHECK (true);
