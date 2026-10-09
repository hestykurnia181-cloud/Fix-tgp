create table if not exists public.deleted_records (
  table_name text not null,
  record_id text not null,
  deleted_at timestamptz not null default now(),
  primary key (table_name, record_id)
);

alter table public.deleted_records enable row level security;

drop policy if exists "Allow public all on deleted_records" on public.deleted_records;

create policy "Allow public all on deleted_records"
  on public.deleted_records
  for all
  to public
  using (true)
  with check (true);

grant select, insert, update, delete on public.deleted_records to anon, authenticated;
