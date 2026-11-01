-- Persist the exact account ID that created a ledger transaction.
-- Nullable/additive so existing application versions remain compatible.
ALTER TABLE public.ledgers
  ADD COLUMN IF NOT EXISTS created_by_user_id TEXT;

-- Backfill records whose existing created_by value is an account username.
UPDATE public.ledgers AS ledger
SET created_by_user_id = app_user.user_id
FROM public.users AS app_user
WHERE ledger.created_by_user_id IS NULL
  AND lower(trim(ledger.created_by)) = lower(trim(app_user.username));

-- Older rows may store a full name instead of a username. Backfill only when
-- that full name resolves to exactly one account, never when names are shared.
UPDATE public.ledgers AS ledger
SET created_by_user_id = matched.user_id
FROM (
  SELECT lower(trim(full_name)) AS normalized_name, MIN(user_id) AS user_id
  FROM public.users
  WHERE full_name IS NOT NULL AND trim(full_name) <> ''
  GROUP BY lower(trim(full_name))
  HAVING COUNT(*) = 1
) AS matched
WHERE ledger.created_by_user_id IS NULL
  AND lower(trim(ledger.created_by)) = matched.normalized_name;

CREATE INDEX IF NOT EXISTS idx_ledgers_business_created_by_user
  ON public.ledgers (business_id, created_by_user_id);
