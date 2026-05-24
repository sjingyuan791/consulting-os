-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Table: workspaces
-- Multi-tenancy root. Each user belongs to a workspace (one-to-one for MVP, can be many-to-many later).
create table workspaces (
    id uuid primary key default uuid_generate_v4(),
    owner_user_id uuid references auth.users(id) not null,
    name text not null,
    created_at timestamptz default now()
);

-- RLS for workspaces
alter table workspaces enable row level security;

create policy "Users can view their own workspace"
    on workspaces for select
    using (auth.uid() = owner_user_id);

create policy "Users can insert their own workspace"
    on workspaces for insert
    with check (auth.uid() = owner_user_id);

create policy "Users can update their own workspace"
    on workspaces for update
    using (auth.uid() = owner_user_id);

-- Table: clients
-- Companies being diagnosed.
create table clients (
    id uuid primary key default uuid_generate_v4(),
    workspace_id uuid references workspaces(id) on delete cascade not null,
    name text not null,
    industry text,
    location text,
    notes text,
    created_at timestamptz default now()
);

-- RLS for clients
alter table clients enable row level security;

create policy "Users can view clients in their workspace"
    on clients for select
    using (
        exists (
            select 1 from workspaces
            where id = clients.workspace_id
            and owner_user_id = auth.uid()
        )
    );

create policy "Users can insert clients in their workspace"
    on clients for insert
    with check (
        exists (
            select 1 from workspaces
            where id = clients.workspace_id
            and owner_user_id = auth.uid()
        )
    );

create policy "Users can update clients in their workspace"
    on clients for update
    using (
        exists (
            select 1 from workspaces
            where id = clients.workspace_id
            and owner_user_id = auth.uid()
        )
    );

create policy "Users can delete clients in their workspace"
    on clients for delete
    using (
        exists (
            select 1 from workspaces
            where id = clients.workspace_id
            and owner_user_id = auth.uid()
        )
    );

-- Table: diagnosis_runs
-- Stores the result of a diagnosis session.
create table diagnosis_runs (
    id uuid primary key default uuid_generate_v4(),
    workspace_id uuid references workspaces(id) on delete cascade not null,
    client_id uuid references clients(id) on delete cascade not null,
    input_meta_json jsonb, -- Metadata of uploaded files
    summary_json jsonb, -- Calculated financial/sales metrics
    report_json jsonb, -- Final LLM generated report structure
    status text check (status in ('processing', 'completed', 'failed')) default 'processing',
    created_at timestamptz default now()
);

-- RLS for diagnosis_runs
alter table diagnosis_runs enable row level security;

create policy "Users can view runs in their workspace"
    on diagnosis_runs for select
    using (
        exists (
            select 1 from workspaces
            where id = diagnosis_runs.workspace_id
            and owner_user_id = auth.uid()
        )
    );

create policy "Users can insert runs in their workspace"
    on diagnosis_runs for insert
    with check (
        exists (
            select 1 from workspaces
            where id = diagnosis_runs.workspace_id
            and owner_user_id = auth.uid()
        )
    );

create policy "Users can update runs in their workspace"
    on diagnosis_runs for update
    using (
        exists (
            select 1 from workspaces
            where id = diagnosis_runs.workspace_id
            and owner_user_id = auth.uid()
        )
    );

-- Table: artifacts
-- generated PDFs, etc.
create table artifacts (
    id uuid primary key default uuid_generate_v4(),
    workspace_id uuid references workspaces(id) on delete cascade not null,
    client_id uuid references clients(id) on delete cascade not null,
    run_id uuid references diagnosis_runs(id) on delete cascade,
    artifact_type text not null, -- 'pdf_report', 'raw_file_placeholder'e
    storage_path_or_local text not null, -- Path in Supabase Storage or local path (for MVP)
    created_at timestamptz default now()
);

-- RLS for artifacts
alter table artifacts enable row level security;

create policy "Users can view artifacts in their workspace"
    on artifacts for select
    using (
        exists (
            select 1 from workspaces
            where id = artifacts.workspace_id
            and owner_user_id = auth.uid()
        )
    );

create policy "Users can insert artifacts in their workspace"
    on artifacts for insert
    with check (
        exists (
            select 1 from workspaces
            where id = artifacts.workspace_id
            and owner_user_id = auth.uid()
        )
    );

-- Create indexes for performance
create index idx_clients_workspace on clients(workspace_id);
create index idx_diagnosis_runs_client on diagnosis_runs(client_id);
create index idx_artifacts_run on artifacts(run_id);
