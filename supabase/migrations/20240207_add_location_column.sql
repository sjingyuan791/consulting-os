-- Migration: Add location column to clients
-- The app uses 'location' but the previous migration added 'region'. 
-- We add 'location' to match the app logic.

alter table clients add column if not exists location text;
