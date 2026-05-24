-- =====================================================
-- 中期経営計画書ドキュメント保存テーブル
-- クライアントごとに1つの計画書を保持（UPSERT方式）
-- =====================================================

CREATE TABLE IF NOT EXISTS midterm_plan_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id TEXT NOT NULL,
  document_json JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- クライアントごとに一意制約（UPSERT用）
CREATE UNIQUE INDEX IF NOT EXISTS idx_midterm_plan_client_unique 
  ON midterm_plan_documents(client_id);

-- パフォーマンス用インデックス
CREATE INDEX IF NOT EXISTS idx_midterm_plan_updated 
  ON midterm_plan_documents(updated_at DESC);

SELECT '20260211_midterm_plan_documents マイグレーション完了' AS status;
