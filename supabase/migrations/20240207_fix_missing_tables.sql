-- Migration: Fix Missing Tables (Workspaces)

create table if not exists workspaces (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null, -- references auth.users(id) but explicit FK might fail if insufficient permissions
  name text not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Policy (Optional: Enable RLS)
alter table workspaces enable row level security;

create policy "Users can view their own workspaces"
  on workspaces for select
  using (auth.uid() = owner_user_id);

create policy "Users can insert their own workspaces"
  on workspaces for insert
  with check (auth.uid() = owner_user_id);
