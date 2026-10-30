-- TGP F&B cashier without STAN, personal sales identity, and STAN-bound damaged-goods evidence.
-- Safe additive migration; apply in Supabase SQL Editor before deploying the updated app.
ALTER TABLE public.sales ADD COLUMN IF NOT EXISTS cashier_user_id TEXT;
ALTER TABLE public.damaged_goods ADD COLUMN IF NOT EXISTS outlet_id TEXT;
ALTER TABLE public.damaged_goods ADD COLUMN IF NOT EXISTS photo_data_url TEXT;
ALTER TABLE public.damaged_goods ADD COLUMN IF NOT EXISTS approved_by TEXT;
ALTER TABLE public.damaged_goods ADD COLUMN IF NOT EXISTS processed_at BIGINT;
ALTER TABLE public.stock_mutations ADD COLUMN IF NOT EXISTS outlet_id TEXT;
ALTER TABLE public.stock_mutations ADD COLUMN IF NOT EXISTS reference_id TEXT;
ALTER TABLE public.stock_mutations ADD COLUMN IF NOT EXISTS performed_by TEXT;

CREATE INDEX IF NOT EXISTS idx_sales_cashier_user_id ON public.sales (business_id, cashier_user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_damaged_goods_outlet_id ON public.damaged_goods (business_id, outlet_id, timestamp DESC);
