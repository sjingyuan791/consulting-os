-- Migration: Financial and Internal Data Categories
-- 財務データ・内部環境データのカテゴリ別保存対応

-- 1. データカテゴリ定義テーブル
CREATE TABLE IF NOT EXISTS data_categories (
  category_id TEXT PRIMARY KEY,
  category_name TEXT NOT NULL,
  category_name_ja TEXT NOT NULL,
  description TEXT,
  sort_order INT DEFAULT 0
);

-- 初期データカテゴリ
INSERT INTO data_categories (category_id, category_name, category_name_ja, description, sort_order) VALUES
  ('financial', 'Financial Data', '財務データ', '決算書、借入、資金繰り等の財務関連データ', 1),
  ('internal', 'Internal Environment', '内部環境データ', '従業員、顧客、商品等の内部環境データ', 2),
  ('external', 'External Environment', '外部環境データ', '市場、競合、業界等の外部環境データ', 3)
ON CONFLICT (category_id) DO NOTHING;

-- 2. データセットタイプ定義テーブル
CREATE TABLE IF NOT EXISTS dataset_types (
  type_id TEXT PRIMARY KEY,
  type_name TEXT NOT NULL,
  type_name_ja TEXT NOT NULL,
  category_id TEXT REFERENCES data_categories(category_id),
  required_columns JSONB,  -- 必須カラム定義
  sample_file TEXT,        -- サンプルファイル名
  description TEXT,
  sort_order INT DEFAULT 0
);

-- 財務データタイプ
INSERT INTO dataset_types (type_id, type_name, type_name_ja, category_id, sample_file, description, sort_order) VALUES
  ('financials', 'Financial Statements', '決算書', 'financial', '01_財務データ/決算書.csv', 'BS/PL 全勘定科目', 1),
  ('loans', 'Loan Details', '借入一覧', 'financial', '01_財務データ/借入一覧.csv', '借入先・返済条件・残高', 2),
  ('monthly', 'Monthly Data', '月次推移', 'financial', '01_財務データ/月次推移.csv', '月次売上・経費・残高', 3),
  ('cashflow_forecast', 'Cash Flow Forecast', '資金繰り予定表', 'financial', '01_財務データ/資金繰り予定表.csv', '入出金予定', 4),
  ('fixed_assets', 'Fixed Assets', '固定資産台帳', 'financial', '01_財務データ/固定資産台帳.csv', '固定資産・減価償却', 5),
  ('budget_actual', 'Budget vs Actual', '予算実績対比', 'financial', '01_財務データ/予算実績対比.csv', '予実管理', 6)
ON CONFLICT (type_id) DO NOTHING;

-- 内部環境データタイプ
INSERT INTO dataset_types (type_id, type_name, type_name_ja, category_id, sample_file, description, sort_order) VALUES
  ('employees', 'Employee List', '従業員一覧', 'internal', '02_内部環境データ/従業員一覧.csv', '人員・給与・資格', 11),
  ('customers', 'Customer List', '得意先一覧', 'internal', '02_内部環境データ/得意先一覧.csv', '取引先・売掛金・与信', 12),
  ('suppliers', 'Supplier List', '仕入先一覧', 'internal', '02_内部環境データ/仕入先一覧.csv', '仕入先・買掛金', 13),
  ('products', 'Products & Inventory', '商品・在庫マスタ', 'internal', '02_内部環境データ/商品・在庫マスタ.csv', '商品・在庫・原価', 14),
  ('sales_detail', 'Sales Details', '売上明細', 'internal', '02_内部環境データ/売上明細.csv', '日次売上明細', 15),
  ('segment_pnl', 'Segment P&L', '部門別損益', 'internal', '02_内部環境データ/部門別損益.csv', '部門・セグメント別収益', 16)
ON CONFLICT (type_id) DO NOTHING;

-- 3. client_datasets テーブルにカテゴリカラム追加
ALTER TABLE client_datasets 
  ADD COLUMN IF NOT EXISTS category_id TEXT REFERENCES data_categories(category_id),
  ADD COLUMN IF NOT EXISTS type_id TEXT REFERENCES dataset_types(type_id),
  ADD COLUMN IF NOT EXISTS display_name TEXT,
  ADD COLUMN IF NOT EXISTS file_name TEXT,
  ADD COLUMN IF NOT EXISTS row_count INT DEFAULT 0;

-- 4. インデックス追加
CREATE INDEX IF NOT EXISTS idx_client_datasets_category ON client_datasets(category_id);
CREATE INDEX IF NOT EXISTS idx_client_datasets_type ON client_datasets(type_id);
CREATE INDEX IF NOT EXISTS idx_dataset_types_category ON dataset_types(category_id);

-- 5. ビュー: クライアント別データ一覧
CREATE OR REPLACE VIEW client_data_summary AS
SELECT 
  cd.client_id,
  c.client_name,
  dc.category_name_ja AS category,
  dt.type_name_ja AS data_type,
  cd.display_name,
  cd.row_count,
  cd.version,
  cd.uploaded_at
FROM client_datasets cd
LEFT JOIN clients c ON cd.client_id = c.client_id
LEFT JOIN data_categories dc ON cd.category_id = dc.category_id
LEFT JOIN dataset_types dt ON cd.type_id = dt.type_id
ORDER BY c.client_name, dc.sort_order, dt.sort_order;
