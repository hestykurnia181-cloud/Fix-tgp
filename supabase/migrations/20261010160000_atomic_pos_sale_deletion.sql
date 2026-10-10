CREATE OR REPLACE FUNCTION public.delete_pos_sale(
  p_sale_id text,
  p_business_id text DEFAULT NULL,
  p_receipt_number text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  v_business_id text;
  v_receipt_number text;
  v_ledger_ids text[] := ARRAY[]::text[];
  v_ledger_count integer := 0;
  v_sale_count integer := 0;
BEGIN
  IF p_sale_id IS NULL OR btrim(p_sale_id) = '' THEN
    RAISE EXCEPTION 'sale_id wajib diisi';
  END IF;

  SELECT s.business_id, s.receipt_number
    INTO v_business_id, v_receipt_number
    FROM public.sales s
   WHERE s.sale_id = p_sale_id;

  v_business_id := COALESCE(v_business_id, p_business_id);
  v_receipt_number := COALESCE(v_receipt_number, p_receipt_number);

  INSERT INTO public.deleted_records(table_name, record_id, deleted_at)
  VALUES ('sales', p_sale_id, now())
  ON CONFLICT (table_name, record_id)
  DO UPDATE SET deleted_at = EXCLUDED.deleted_at;

  IF v_business_id IS NOT NULL THEN
    SELECT COALESCE(array_agg(l.transaction_id), ARRAY[]::text[])
      INTO v_ledger_ids
      FROM public.ledgers l
     WHERE l.business_id = v_business_id
       AND l.reference_id = ANY(array_remove(ARRAY[v_receipt_number, p_sale_id]::text[], NULL));

    INSERT INTO public.deleted_records(table_name, record_id, deleted_at)
    SELECT 'ledgers', l.transaction_id, now()
      FROM public.ledgers l
     WHERE l.business_id = v_business_id
       AND l.reference_id = ANY(array_remove(ARRAY[v_receipt_number, p_sale_id]::text[], NULL))
    ON CONFLICT (table_name, record_id)
    DO UPDATE SET deleted_at = EXCLUDED.deleted_at;

    DELETE FROM public.ledgers l
     WHERE l.business_id = v_business_id
       AND l.reference_id = ANY(array_remove(ARRAY[v_receipt_number, p_sale_id]::text[], NULL));
    GET DIAGNOSTICS v_ledger_count = ROW_COUNT;
  END IF;

  DELETE FROM public.sales WHERE sale_id = p_sale_id;
  GET DIAGNOSTICS v_sale_count = ROW_COUNT;

  RETURN jsonb_build_object(
    'success', true,
    'sale_id', p_sale_id,
    'sale_rows_deleted', v_sale_count,
    'ledger_rows_deleted', v_ledger_count,
    'ledger_ids', to_jsonb(v_ledger_ids),
    'tombstoned', true
  );
END;
$$;

GRANT EXECUTE ON FUNCTION public.delete_pos_sale(text, text, text) TO anon, authenticated;
