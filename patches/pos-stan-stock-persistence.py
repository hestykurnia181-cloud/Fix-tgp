from pathlib import Path

ROOT = Path('project')
p = ROOT / 'src/services/supabaseSyncService.ts'
s = p.read_text(encoding='utf-8')
old = """  public async syncOutletStocks(stocks: OutletStockEntity[]) {
    const supabase = getSupabaseClient();
    if (!supabase) return;
    try {
      await supabase.from('outlet_stocks').upsert(stocks.map(mapOutletStockToDb));
      if (this.channel) {
        this.channel.send({
          type: 'broadcast',
          event: 'tgp_mutation',
          payload: { type: 'INSERT_OR_UPDATE', table: 'outlet_stocks' },
        });
      }
    } catch (e) {
      console.warn('[SupabaseSync] Batch outlet_stocks upsert error:', e);
    }
  }"""
new = """  public async syncOutletStocks(stocks: OutletStockEntity[]) {
    if (!stocks.length) return;
    // Use the same durable retry queue and tombstone checks as single-row stock writes.
    // The old direct batch upsert ignored Supabase's returned { error }, so POS sales
    // could succeed while STAN stock writes silently failed and were never retried.
    await Promise.all(stocks.map((stock) =>
      this.safeUpsertRecord('outlet_stocks', mapOutletStockToDb(stock))
    ));
  }"""
if new not in s:
    if old not in s:
        raise SystemExit('syncOutletStocks anchor missing')
    s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

p = ROOT / 'src/context/TgpContext.tsx'
s = p.read_text(encoding='utf-8')
old_find = """            (os) => os.outletId === targetOutlet.outletId && os.itemId === cartItem.item.itemId
"""
new_find = """            (os) => os.businessId === effectiveBusinessId && os.outletId === targetOutlet.outletId && os.itemId === cartItem.item.itemId
"""
if new_find not in s:
    if old_find not in s:
        raise SystemExit('POS stock validation lookup anchor missing')
    s = s.replace(old_find, new_find, 1)

old_update = """          if (os.outletId === targetOutlet.outletId) {
            const cartEntry = posCart.find((ci) => ci.item.itemId === os.itemId);
"""
new_update = """          if (os.businessId === effectiveBusinessId && os.outletId === targetOutlet.outletId) {
            const cartEntry = posCart.find((ci) => ci.item.itemId === os.itemId && ci.item.type !== 'SERVICE');
"""
if new_update not in s:
    if old_update not in s:
        raise SystemExit('POS stock decrement scope anchor missing')
    s = s.replace(old_update, new_update, 1)

old_sync = """      supabaseSyncService.syncOutletStocks(changedOutletStocks);
"""
new_sync = """      await supabaseSyncService.syncOutletStocks(changedOutletStocks);
"""
if new_sync not in s:
    if old_sync not in s:
        raise SystemExit('POS stock sync call anchor missing')
    s = s.replace(old_sync, new_sync, 1)

p.write_text(s, encoding='utf-8')
print('Fixed POS STAN stock persistence retry handling and business/outlet-scoped decrement.')
