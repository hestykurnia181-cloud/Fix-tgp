-- TGP cashier identity, STAN-bound damage evidence, and stock movement scope.
-- Add only columns confirmed missing in the connected production schema.
ALTER TABLE public.sales
  ADD COLUMN IF NOT EXISTS cashier_user_id TEXT;

ALTER TABLE public.damaged_goods
  ADD COLUMN IF NOT EXISTS outlet_id TEXT,
  ADD COLUMN IF NOT EXISTS photo_data_url TEXT;

ALTER TABLE public.stock_mutations
  ADD COLUMN IF NOT EXISTS outlet_id TEXT;

CREATE INDEX IF NOT EXISTS idx_sales_cashier_user_id
  ON public.sales (business_id, cashier_user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_damaged_goods_outlet_id
  ON public.damaged_goods (business_id, outlet_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_stock_mutations_outlet_id
  ON public.stock_mutations (business_id, outlet_id, timestamp DESC);
