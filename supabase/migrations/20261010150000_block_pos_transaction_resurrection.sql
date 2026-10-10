-- Prevent deleted POS sales and ledger rows from being recreated by stale/offline clients.
-- Existing deletion markers are authoritative; remove any rows that were resurrected before this guard.
create or replace function public.block_resurrection_of_deleted_pos_records()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
declare
  target_id text;
  target_table text;
begin
  if TG_TABLE_NAME = 'sales' then
    target_table := 'sales';
    target_id := NEW.sale_id;
  elsif TG_TABLE_NAME = 'ledgers' then
    target_table := 'ledgers';
    target_id := NEW.transaction_id;
  else
    return NEW;
  end if;

  if target_id is not null and exists (
    select 1
    from public.deleted_records d
    where d.table_name = target_table
      and d.record_id = target_id
  ) then
    raise exception 'POS record %/% was permanently deleted; stale sync write blocked', target_table, target_id
      using errcode = '23514';
  end if;

  return NEW;
end;
$$;

drop trigger if exists block_deleted_sales_resurrection on public.sales;
create trigger block_deleted_sales_resurrection
before insert or update on public.sales
for each row execute function public.block_resurrection_of_deleted_pos_records();

drop trigger if exists block_deleted_ledgers_resurrection on public.ledgers;
create trigger block_deleted_ledgers_resurrection
before insert or update on public.ledgers
for each row execute function public.block_resurrection_of_deleted_pos_records();

delete from public.ledgers l
using public.deleted_records d
where d.table_name = 'ledgers'
  and d.record_id = l.transaction_id;

delete from public.sales s
using public.deleted_records d
where d.table_name = 'sales'
  and d.record_id = s.sale_id;
