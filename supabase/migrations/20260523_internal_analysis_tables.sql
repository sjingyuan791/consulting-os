-- =====================================================
-- 内部環境分析ワークスペース用テーブル
-- 適用方法: Supabase Dashboard > SQL Editor で実行
-- =====================================================

-- セッション管理 + AI質問格納
create table if not exists internal_sessions (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(id) on delete cascade,
  session_name text not null,
  purpose text,
  phase text,
  external_analysis_summary text,
  financial_analysis_summary text,
  strategy_hypotheses text,
  output_purpose text[] default '{}',
  analysis_depth text,
  consultant_name text,
  version int default 1,
  status text default 'active',
  ai_questions jsonb default '[]',
  documents jsonb default '[]',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 8ドメインの発見事項（行レベルメタデータ）
create table if not exists internal_findings_items (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references internal_sessions(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  domain text not null,
  item_name text not null,
  description text,
  classification text default 'unclassified',
  source text default 'unknown',
  confidence text default 'unknown',
  status text default 'unconfirmed',
  note text,
  evidence text,
  impact_on_profit text,
  impact_on_cashflow text,
  impact_on_strategy text,
  swot_candidate text default 'neither',
  adoption_status text default 'pending',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create or replace function internal_update_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

do $$ begin
  if not exists (select 1 from pg_trigger where tgname = 'internal_sessions_updated_at') then
    create trigger internal_sessions_updated_at
      before update on internal_sessions for each row execute function internal_update_updated_at();
  end if;
  if not exists (select 1 from pg_trigger where tgname = 'internal_findings_items_updated_at') then
    create trigger internal_findings_items_updated_at
      before update on internal_findings_items for each row execute function internal_update_updated_at();
  end if;
end $$;
