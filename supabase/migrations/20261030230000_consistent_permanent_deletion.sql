-- Durable deletion markers for every application table; stale/offline clients cannot resurrect deleted rows.
CREATE OR REPLACE FUNCTION public.tgp_record_deleted_row()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public AS $$
DECLARE v_id text; v_key text;
BEGIN
  v_key := CASE TG_TABLE_NAME
    WHEN 'businesses' THEN 'business_id' WHEN 'users' THEN 'user_id'
    WHEN 'items' THEN 'item_id' WHEN 'sales' THEN 'sale_id'
    WHEN 'ledgers' THEN 'transaction_id' WHEN 'transfers' THEN 'transfer_id'
    WHEN 'damaged_goods' THEN 'report_id' WHEN 'attendances' THEN 'attendance_id'
    WHEN 'outlets' THEN 'outlet_id' WHEN 'outlet_stocks' THEN 'stock_id'
    WHEN 'stan_transfers' THEN 'transfer_id' WHEN 'stock_mutations' THEN 'mutation_id'
    WHEN 'audit_logs' THEN 'log_id' WHEN 'operational_periods' THEN 'period_id'
    ELSE NULL END;
  IF v_key IS NULL THEN RAISE EXCEPTION 'No deletion key configured for %',TG_TABLE_NAME; END IF;
  v_id := to_jsonb(OLD)->>v_key;
  IF v_id IS NOT NULL AND v_id<>'' THEN
    INSERT INTO public.deleted_records(table_name,record_id,deleted_at)
    VALUES(TG_TABLE_NAME,v_id,now()) ON CONFLICT(table_name,record_id) DO NOTHING;
  END IF;
  RETURN OLD;
END $$;

CREATE OR REPLACE FUNCTION public.tgp_block_deleted_row_resurrection()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public AS $$
DECLARE v_id text; v_key text;
BEGIN
  v_key := CASE TG_TABLE_NAME
    WHEN 'businesses' THEN 'business_id' WHEN 'users' THEN 'user_id'
    WHEN 'items' THEN 'item_id' WHEN 'sales' THEN 'sale_id'
    WHEN 'ledgers' THEN 'transaction_id' WHEN 'transfers' THEN 'transfer_id'
    WHEN 'damaged_goods' THEN 'report_id' WHEN 'attendances' THEN 'attendance_id'
    WHEN 'outlets' THEN 'outlet_id' WHEN 'outlet_stocks' THEN 'stock_id'
    WHEN 'stan_transfers' THEN 'transfer_id' WHEN 'stock_mutations' THEN 'mutation_id'
    WHEN 'audit_logs' THEN 'log_id' WHEN 'operational_periods' THEN 'period_id'
    ELSE NULL END;
  IF v_key IS NULL THEN RAISE EXCEPTION 'No resurrection key configured for %',TG_TABLE_NAME; END IF;
  v_id := to_jsonb(NEW)->>v_key;
  IF v_id IS NOT NULL AND EXISTS(SELECT 1 FROM public.deleted_records d WHERE d.table_name=TG_TABLE_NAME AND d.record_id=v_id) THEN
    RAISE EXCEPTION 'Record %/% was permanently deleted; stale sync write blocked',TG_TABLE_NAME,v_id USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;

REVOKE ALL ON FUNCTION public.tgp_record_deleted_row() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.tgp_block_deleted_row_resurrection() FROM PUBLIC,anon,authenticated;

-- Clients can read tombstones for sync checks, but cannot forge, modify, or erase them.
DROP POLICY IF EXISTS "Allow public all on deleted_records" ON public.deleted_records;
DROP POLICY IF EXISTS "Read deletion markers for sync guard" ON public.deleted_records;
REVOKE ALL ON TABLE public.deleted_records FROM PUBLIC,anon,authenticated;
GRANT SELECT ON TABLE public.deleted_records TO anon,authenticated;
CREATE POLICY "Read deletion markers for sync guard" ON public.deleted_records
  FOR SELECT TO anon,authenticated USING(true);

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['businesses','users','items','sales','ledgers','transfers','damaged_goods','attendances','outlets','outlet_stocks','stan_transfers','stock_mutations','audit_logs','operational_periods'] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS tgp_capture_deleted_row ON public.%I',t);
    EXECUTE format('CREATE TRIGGER tgp_capture_deleted_row AFTER DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.tgp_record_deleted_row()',t);
    EXECUTE format('DROP TRIGGER IF EXISTS tgp_prevent_deleted_row_resurrection ON public.%I',t);
    EXECUTE format('CREATE TRIGGER tgp_prevent_deleted_row_resurrection BEFORE INSERT OR UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.tgp_block_deleted_row_resurrection()',t);
  END LOOP;
END $$;

-- Atomic catalogue-item removal: all STAN stock rows and the catalogue row are deleted together.
CREATE OR REPLACE FUNCTION public.delete_tgp_item(p_item_id text)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=public AS $$
DECLARE v_stock_ids text[]:=ARRAY[]::text[]; v_deleted integer:=0;
BEGIN
  IF p_item_id IS NULL OR btrim(p_item_id)='' THEN RAISE EXCEPTION 'item_id wajib diisi'; END IF;
  SELECT COALESCE(array_agg(stock_id),ARRAY[]::text[]) INTO v_stock_ids FROM public.outlet_stocks WHERE item_id=p_item_id;
  DELETE FROM public.outlet_stocks WHERE item_id=p_item_id;
  UPDATE public.items i SET bom_ingredients=COALESCE((
    SELECT jsonb_agg(e) FROM jsonb_array_elements(COALESCE(i.bom_ingredients,'[]'::jsonb)) e
    WHERE e->>'rawItemId' IS DISTINCT FROM p_item_id
  ),'[]'::jsonb), updated_at=(extract(epoch FROM clock_timestamp())*1000)::bigint
  WHERE i.bom_ingredients @> jsonb_build_array(jsonb_build_object('rawItemId',p_item_id));
  DELETE FROM public.items WHERE item_id=p_item_id;
  GET DIAGNOSTICS v_deleted=ROW_COUNT;
  IF v_deleted<>1 THEN RAISE EXCEPTION 'Barang tidak ditemukan atau tidak dapat dihapus'; END IF;
  RETURN jsonb_build_object('success',true,'item_rows_deleted',v_deleted,'stock_ids',to_jsonb(v_stock_ids));
END $$;
GRANT EXECUTE ON FUNCTION public.delete_tgp_item(text) TO anon,authenticated;

-- Remove live STAN data and links; retain financial/damage history with its outlet-name snapshot.
CREATE OR REPLACE FUNCTION public.delete_tgp_outlet(p_outlet_id text)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=public AS $$
DECLARE v_name text; v_stock_ids text[]:=ARRAY[]::text[]; v_transfer_ids text[]:=ARRAY[]::text[];
 v_mutation_ids text[]:=ARRAY[]::text[]; v_deleted integer:=0;
BEGIN
  IF p_outlet_id IS NULL OR btrim(p_outlet_id)='' THEN RAISE EXCEPTION 'outlet_id wajib diisi'; END IF;
  SELECT name INTO v_name FROM public.outlets WHERE outlet_id=p_outlet_id;
  IF v_name IS NULL THEN RAISE EXCEPTION 'STAN tidak ditemukan'; END IF;
  SELECT COALESCE(array_agg(stock_id),ARRAY[]::text[]) INTO v_stock_ids FROM public.outlet_stocks WHERE outlet_id=p_outlet_id;
  SELECT COALESCE(array_agg(transfer_id),ARRAY[]::text[]) INTO v_transfer_ids FROM public.stan_transfers WHERE outlet_id=p_outlet_id;
  SELECT COALESCE(array_agg(mutation_id),ARRAY[]::text[]) INTO v_mutation_ids FROM public.stock_mutations WHERE outlet_id=p_outlet_id;
  DELETE FROM public.outlet_stocks WHERE outlet_id=p_outlet_id;
  DELETE FROM public.stan_transfers WHERE outlet_id=p_outlet_id;
  DELETE FROM public.stock_mutations WHERE outlet_id=p_outlet_id;
  UPDATE public.users SET outlet_id=NULL WHERE outlet_id=p_outlet_id;
  UPDATE public.sales SET outlet_id=NULL,outlet_name=COALESCE(outlet_name,v_name) WHERE outlet_id=p_outlet_id;
  UPDATE public.ledgers SET outlet_id=NULL,outlet_name=COALESCE(outlet_name,v_name) WHERE outlet_id=p_outlet_id;
  UPDATE public.damaged_goods SET outlet_id=NULL WHERE outlet_id=p_outlet_id;
  DELETE FROM public.outlets WHERE outlet_id=p_outlet_id;
  GET DIAGNOSTICS v_deleted=ROW_COUNT;
  IF v_deleted<>1 THEN RAISE EXCEPTION 'STAN tidak berhasil dihapus'; END IF;
  RETURN jsonb_build_object('success',true,'outlet_rows_deleted',v_deleted,'stock_ids',to_jsonb(v_stock_ids),'stan_transfer_ids',to_jsonb(v_transfer_ids),'mutation_ids',to_jsonb(v_mutation_ids));
END $$;
GRANT EXECUTE ON FUNCTION public.delete_tgp_outlet(text) TO anon,authenticated;

-- Sale, receipt journals, and stock restoration now commit or roll back as one transaction.
CREATE OR REPLACE FUNCTION public.delete_pos_sale(p_sale_id text,p_business_id text DEFAULT NULL,p_receipt_number text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=public AS $$
DECLARE v_business_id text; v_receipt text; v_outlet_id text; v_items jsonb;
 v_ledger_ids text[]:=ARRAY[]::text[]; v_ledger_count integer:=0; v_sale_count integer:=0;
 v_line jsonb; v_item_id text; v_qty numeric; v_type text;
BEGIN
  IF p_sale_id IS NULL OR btrim(p_sale_id)='' THEN RAISE EXCEPTION 'sale_id wajib diisi'; END IF;
  SELECT business_id,receipt_number,outlet_id,COALESCE(items,'[]'::jsonb)
    INTO v_business_id,v_receipt,v_outlet_id,v_items FROM public.sales WHERE sale_id=p_sale_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Transaksi tidak ditemukan di database'; END IF;
  v_business_id:=COALESCE(v_business_id,p_business_id); v_receipt:=COALESCE(v_receipt,p_receipt_number);
  IF v_business_id IS NOT NULL THEN
    SELECT COALESCE(array_agg(transaction_id),ARRAY[]::text[]) INTO v_ledger_ids FROM public.ledgers
    WHERE business_id=v_business_id AND reference_id=ANY(array_remove(ARRAY[v_receipt,p_sale_id]::text[],NULL));
  END IF;
  FOR v_line IN SELECT value FROM jsonb_array_elements(v_items) LOOP
    v_item_id:=COALESCE(v_line->>'itemId',v_line->>'item_id');
    v_qty:=COALESCE(NULLIF(v_line->>'quantity','')::numeric,0);
    v_type:=upper(COALESCE(v_line->>'itemType',v_line->>'item_type',''));
    IF v_item_id IS NOT NULL AND v_qty>0 AND v_type<>'SERVICE' THEN
      IF v_outlet_id IS NOT NULL THEN
        UPDATE public.outlet_stocks SET stock_quantity=stock_quantity+v_qty,updated_at=(extract(epoch FROM clock_timestamp())*1000)::bigint
        WHERE outlet_id=v_outlet_id AND business_id=v_business_id AND item_id=v_item_id;
      ELSE
        UPDATE public.items SET stock_quantity=stock_quantity+v_qty,updated_at=(extract(epoch FROM clock_timestamp())*1000)::bigint
        WHERE business_id=v_business_id AND item_id=v_item_id;
      END IF;
    END IF;
  END LOOP;
  IF v_business_id IS NOT NULL THEN
    DELETE FROM public.ledgers WHERE business_id=v_business_id AND reference_id=ANY(array_remove(ARRAY[v_receipt,p_sale_id]::text[],NULL));
    GET DIAGNOSTICS v_ledger_count=ROW_COUNT;
  END IF;
  DELETE FROM public.sales WHERE sale_id=p_sale_id;
  GET DIAGNOSTICS v_sale_count=ROW_COUNT;
  IF v_sale_count<>1 THEN RAISE EXCEPTION 'Transaksi tidak berhasil dihapus'; END IF;
  RETURN jsonb_build_object('success',true,'sale_id',p_sale_id,'sale_rows_deleted',v_sale_count,'ledger_rows_deleted',v_ledger_count,'ledger_ids',to_jsonb(v_ledger_ids),'tombstoned',true,'stock_restored',true);
END $$;
GRANT EXECUTE ON FUNCTION public.delete_pos_sale(text,text,text) TO anon,authenticated;
