-- =====================================================
-- 財務分析ワークスペース用テーブル (STEP 0-11)
-- 適用方法: Supabase Dashboard > SQL Editor で実行
-- =====================================================

-- STEP 0: セッション管理（STEP 1,6,7,8 のデータも内包）
create table if not exists fin_sessions (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(id) on delete cascade,
  session_name text not null,
  purpose text,
  phase text,
  target_periods text[] default '{}',
  output_purpose text[] default '{}',
  analysis_depth text,
  consultant_name text,
  version int default 1,
  status text default 'active',
  documents jsonb default '[]',
  cashflow_data jsonb default '{}',
  benchmark_data jsonb default '{}',
  missing_data jsonb default '[]',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- STEP 2: PL/BS（年度ごと1行）
create table if not exists fin_statements (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references fin_sessions(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  fiscal_year text not null,
  pl jsonb default '{}',
  bs jsonb default '{}',
  abnormal_memos jsonb default '[]',
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(session_id, fiscal_year)
);

-- STEP 3: 借入明細
create table if not exists fin_loans (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references fin_sessions(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  lender_name text,
  balance numeric default 0,
  annual_principal numeric default 0,
  annual_interest numeric default 0,
  remaining_years numeric default 0,
  purpose text,
  collateral text,
  has_schedule boolean default false,
  status text default 'unconfirmed',
  note text,
  created_at timestamptz default now()
);

-- STEP 4: 一時要因・平年化補正
create table if not exists fin_adjustments (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references fin_sessions(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  fiscal_year text not null,
  item_name text not null,
  amount numeric default 0,
  category text,
  adjustment_direction text default 'pending',
  source text default 'unknown',
  confidence text default 'unknown',
  adoption_status text default 'pending',
  note text,
  created_at timestamptz default now()
);

-- STEP 5: 売上セグメント
create table if not exists fin_segments (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references fin_sessions(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  fiscal_year text not null,
  segment_name text not null,
  sales_amount numeric default 0,
  sales_share numeric default 0,
  gross_margin numeric default 0,
  order_count int default 0,
  average_unit_price numeric default 0,
  sales_route text default 'unknown',
  control_type text default 'unknown',
  price_control text,
  cash_collection_quality text,
  operational_burden text,
  data_source text default 'unknown',
  data_confidence text default 'unknown',
  consultant_note text,
  ai_hypothesis text,
  falsification_condition text,
  missing_data text,
  strategic_treatment text default 'unknown',
  adoption_status text default 'pending',
  created_at timestamptz default now()
);

-- STEP 9/10: AI分析結果・採用可否
create table if not exists fin_analysis_results (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references fin_sessions(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  fiscal_year text,
  analysis_type text not null,
  ai_output jsonb default '{}',
  evidence text,
  confidence text default 'medium',
  consultant_review text,
  adoption_status text default 'pending',
  revision_note text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- updated_at 自動更新
create or replace function fin_update_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

do $$ begin
  if not exists (select 1 from pg_trigger where tgname = 'fin_sessions_updated_at') then
    create trigger fin_sessions_updated_at
      before update on fin_sessions for each row execute function fin_update_updated_at();
  end if;
  if not exists (select 1 from pg_trigger where tgname = 'fin_statements_updated_at') then
    create trigger fin_statements_updated_at
      before update on fin_statements for each row execute function fin_update_updated_at();
  end if;
  if not exists (select 1 from pg_trigger where tgname = 'fin_analysis_results_updated_at') then
    create trigger fin_analysis_results_updated_at
      before update on fin_analysis_results for each row execute function fin_update_updated_at();
  end if;
end $$;
