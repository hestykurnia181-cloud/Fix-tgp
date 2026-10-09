from pathlib import Path

root = Path("project")

# MASTER sees every sale; OWNER remains limited to the businesses they are authorized to manage.
p = root / "src/context/TgpContext.tsx"
s = p.read_text()
old = """  const globalOwnerSales = currentSession?.user.role === UserRole.OWNER
    ? sales.filter((s) => authorizedBusinesses.some((b) => b.businessId === s.businessId))
    : [];
"""
new = """  const globalOwnerSales = normalizeUserRole(currentSession?.user.role) === UserRole.MASTER
    ? sales
    : normalizeUserRole(currentSession?.user.role) === UserRole.OWNER
      ? sales.filter((s) => authorizedBusinesses.some((b) => b.businessId === s.businessId))
      : [];
"""
if new not in s:
    if old not in s:
        raise RuntimeError("globalOwnerSales visibility anchor missing")
    s = s.replace(old, new, 1)
    p.write_text(s)
    print("MASTER transaction visibility fixed")
else:
    print("MASTER transaction visibility already fixed")

# Delete all financial ledger rows tied to this receipt and then delete the sale row.
# The commission and owner-share amounts are columns on the sale itself, so deleting the
# sale row removes those financial values too. If the sale delete fails, restore ledgers.
p = root / "src/services/supabaseSyncService.ts"
s = p.read_text()
start = s.find("  public async deleteSale(sale: SaleOrderEntity): Promise<boolean> {")
end = s.find("  public async deleteUserAccount(userId: string): Promise<boolean> {", start)
if start < 0 or end < 0:
    raise RuntimeError("deleteSale method boundaries missing")
new_method = """  public async deleteSale(sale: SaleOrderEntity): Promise<boolean> {
    const supabase = getSupabaseClient();
    if (!supabase || !sale?.saleId || !sale?.businessId || !sale?.receiptNumber) return false;

    let linkedLedgers: any[] = [];
    let ledgersRemoved = false;
    try {
      // Read every ledger row associated with this receipt, not only PENJUALAN_POS,
      // so service-related income/commission journal rows cannot be left behind.
      const { data: ledgerRows, error: readLedgerError } = await supabase
        .from('ledgers')
        .select('*')
        .eq('business_id', sale.businessId)
        .eq('reference_id', sale.receiptNumber);
      if (readLedgerError) throw readLedgerError;
      linkedLedgers = ledgerRows || [];

      const { error: ledgerError } = await supabase.from('ledgers').delete()
        .eq('business_id', sale.businessId)
        .eq('reference_id', sale.receiptNumber);
      if (ledgerError) throw ledgerError;
      ledgersRemoved = true;

      // Request the deleted row back so a zero-row/RLS no-op is not reported as success.
      const { data: deletedSales, error: saleError } = await supabase
        .from('sales')
        .delete()
        .eq('sale_id', sale.saleId)
        .select('sale_id');
      if (saleError) throw saleError;
      if (!deletedSales || deletedSales.length === 0) {
        throw new Error('Transaksi tidak ditemukan di Supabase atau tidak dapat dihapus.');
      }

      if (this.channel) {
        this.channel.send({ type: 'broadcast', event: 'tgp_mutation', payload: { type: 'INSERT_OR_UPDATE', table: 'sales' } });
        this.channel.send({ type: 'broadcast', event: 'tgp_mutation', payload: { type: 'INSERT_OR_UPDATE', table: 'ledgers' } });
      }
      return true;
    } catch (error) {
      console.warn('[SupabaseSync] deleteSale failed:', error);
      // Avoid losing the journal if deleting the sale itself fails.
      if (ledgersRemoved && linkedLedgers.length) {
        try {
          const { error: restoreError } = await supabase.from('ledgers').upsert(linkedLedgers);
          if (restoreError) console.error('[SupabaseSync] ledger rollback failed:', restoreError);
        } catch (restoreError) {
          console.error('[SupabaseSync] ledger rollback exception:', restoreError);
        }
      }
      return false;
    }
  }

"""
s = s[:start] + new_method + s[end:]
p.write_text(s)
print("Financially complete sale deletion patched")
