-- =====================================================
-- Consulting OS: クリーン初期化マイグレーション
-- 外部キー制約なしで安全に作成
-- =====================================================

-- =====================================================
-- STEP 1: クライアントマスタ
-- =====================================================
CREATE TABLE IF NOT EXISTS clients (
  client_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  client_name TEXT NOT NULL,
  industry TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- =====================================================
-- STEP 2: データカテゴリ（外部キーなし）
-- =====================================================
CREATE TABLE IF NOT EXISTS data_categories (
  category_id TEXT PRIMARY KEY,
  category_name TEXT NOT NULL,
  category_name_ja TEXT NOT NULL,
  description TEXT,
  sort_order INT DEFAULT 0
);

INSERT INTO data_categories (category_id, category_name, category_name_ja, description, sort_order) VALUES
  ('financial', 'Financial Data', '財務データ', '決算書、借入、資金繰り等', 1),
  ('internal', 'Internal Environment', '内部環境データ', '従業員、顧客、商品等', 2),
  ('external', 'External Environment', '外部環境データ', '市場、競合、業界等', 3)
ON CONFLICT (category_id) DO NOTHING;

-- =====================================================
-- STEP 3: データセットタイプ（外部キーなし）
-- =====================================================
CREATE TABLE IF NOT EXISTS dataset_types (
  type_id TEXT PRIMARY KEY,
  type_name TEXT NOT NULL,
  type_name_ja TEXT NOT NULL,
  category_id TEXT,
  sample_file TEXT,
  description TEXT,
  sort_order INT DEFAULT 0
);

-- 財務データタイプ
INSERT INTO dataset_types (type_id, type_name, type_name_ja, category_id, sample_file, description, sort_order) VALUES
  ('financials', 'Financial Statements', '決算書', 'financial', '01_財務データ/決算書.csv', 'BS/PL全勘定科目', 1),
  ('loans', 'Loan Details', '借入一覧', 'financial', '01_財務データ/借入一覧.csv', '借入先・返済条件', 2),
  ('monthly', 'Monthly Data', '月次推移', 'financial', '01_財務データ/月次推移.csv', '月次売上・経費', 3),
  ('cashflow_forecast', 'Cash Flow Forecast', '資金繰り予定表', 'financial', '01_財務データ/資金繰り予定表.csv', '入出金予定', 4),
  ('fixed_assets', 'Fixed Assets', '固定資産台帳', 'financial', '01_財務データ/固定資産台帳.csv', '固定資産', 5),
  ('budget_actual', 'Budget vs Actual', '予算実績対比', 'financial', '01_財務データ/予算実績対比.csv', '予実管理', 6)
ON CONFLICT (type_id) DO NOTHING;

-- 内部環境データタイプ
INSERT INTO dataset_types (type_id, type_name, type_name_ja, category_id, sample_file, description, sort_order) VALUES
  ('employees', 'Employee List', '従業員一覧', 'internal', '02_内部環境データ/従業員一覧.csv', '人員・給与', 11),
  ('customers', 'Customer List', '得意先一覧', 'internal', '02_内部環境データ/得意先一覧.csv', '取引先・売掛金', 12),
  ('suppliers', 'Supplier List', '仕入先一覧', 'internal', '02_内部環境データ/仕入先一覧.csv', '仕入先・買掛金', 13),
  ('products', 'Products', '商品・在庫マスタ', 'internal', '02_内部環境データ/商品・在庫マスタ.csv', '商品・在庫', 14),
  ('sales_detail', 'Sales Details', '売上明細', 'internal', '02_内部環境データ/売上明細.csv', '日次売上', 15),
  ('segment_pnl', 'Segment P&L', '部門別損益', 'internal', '02_内部環境データ/部門別損益.csv', '部門別収益', 16)
ON CONFLICT (type_id) DO NOTHING;

-- =====================================================
-- STEP 4: クライアントデータセット（外部キーなし）
-- =====================================================
CREATE TABLE IF NOT EXISTS client_datasets (
  dataset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID,
  dataset_type TEXT NOT NULL,
  category_id TEXT,
  type_id TEXT,
  display_name TEXT,
  file_name TEXT,
  data_json JSONB,
  quality_json JSONB,
  row_count INT DEFAULT 0,
  version INT DEFAULT 1,
  uploaded_at TIMESTAMPTZ DEFAULT now()
);

-- =====================================================
-- STEP 5: クライアント分析結果（外部キーなし）
-- =====================================================
CREATE TABLE IF NOT EXISTS client_analysis_runs (
  run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID,
  financial_metrics_json JSONB,
  sales_metrics_json JSONB,
  strategy_context_json JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- =====================================================
-- STEP 6: インデックス
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_client_datasets_client_id ON client_datasets(client_id);
CREATE INDEX IF NOT EXISTS idx_client_datasets_category ON client_datasets(category_id);
CREATE INDEX IF NOT EXISTS idx_client_analysis_runs_client_id ON client_analysis_runs(client_id);

-- =====================================================
-- 完了メッセージ
-- =====================================================
SELECT 'マイグレーション完了' AS status;
