from pathlib import Path
import re

ROOT = Path("project")
sync = ROOT / "src/services/supabaseSyncService.ts"
s = sync.read_text()

# Persistent server tombstones prevent an offline device's old queue from resurrecting deleted rows.
helpers = r"""
  private getRecordIdForTable(table: string, data: any): string | null {
    const keys: Record<string, string[]> = {
      businesses: ['business_id', 'businessId'],
      users: ['user_id', 'userId'],
      items: ['item_id', 'itemId'],
      sales: ['sale_id', 'saleId'],
      ledgers: ['transaction_id', 'transactionId'],
      transfers: ['transfer_id', 'transferId'],
      damaged_goods: ['report_id', 'reportId'],
      attendances: ['attendance_id', 'attendanceId'],
      outlets: ['outlet_id', 'outletId'],
      outlet_stocks: ['stock_id', 'stockId'],
      stan_transfers: ['transfer_id', 'transferId'],
      stock_mutations: ['mutation_id', 'mutationId'],
      audit_logs: ['log_id', 'logId'],
      operational_periods: ['period_id', 'periodId'],
    };
    for (const key of (keys[table] || ['id'])) {
      const value = data?.[key];
      if (value !== undefined && value !== null && String(value) !== '') return String(value);
    }
    return null;
  }

  private async isRecordTombstoned(table: string, recordId: string): Promise<boolean> {
    const supabase = getSupabaseClient();
    if (!supabase) throw new Error('Supabase tidak tersedia saat memeriksa status penghapusan.');
    const { data, error } = await supabase.from('deleted_records')
      .select('record_id')
      .eq('table_name', table)
      .eq('record_id', recordId)
      .maybeSingle();
    if (error) throw error;
    return Boolean(data);
  }

  private clearPendingSyncForRecord(table: string, recordId: string) {
    const rows = this.readPendingSync();
    const keys: Record<string, string[]> = {
      businesses: ['business_id', 'businessId'], users: ['user_id', 'userId'],
      items: ['item_id', 'itemId'], sales: ['sale_id', 'saleId'],
      ledgers: ['transaction_id', 'transactionId'], transfers: ['transfer_id', 'transferId'],
      damaged_goods: ['report_id', 'reportId'], attendances: ['attendance_id', 'attendanceId'],
      outlets: ['outlet_id', 'outletId'], outlet_stocks: ['stock_id', 'stockId'],
      stan_transfers: ['transfer_id', 'transferId'], stock_mutations: ['mutation_id', 'mutationId'],
      audit_logs: ['log_id', 'logId'], operational_periods: ['period_id', 'periodId'],
    };
    const idKeys = keys[table] || ['id'];
    this.writePendingSync(rows.filter((row: any) => {
      if (row?.table !== table) return true;
      if (row?.id === table + ':' + recordId) return false;
      return !idKeys.some((key) => row?.data?.[key] != null && String(row.data[key]) === recordId);
    }));
  }

  private async markRecordDeleted(table: string, recordId: string) {
    const supabase = getSupabaseClient();
    if (!supabase) throw new Error('Supabase tidak tersedia untuk mencatat penghapusan.');
    const { error } = await supabase.from('deleted_records').upsert({
      table_name: table, record_id: String(recordId), deleted_at: new Date().toISOString()
    }, { onConflict: 'table_name,record_id' });
    if (error) throw error;
    this.clearPendingSyncForRecord(table, String(recordId));
  }

  private async unmarkRecordDeleted(table: string, recordId: string) {
    const supabase = getSupabaseClient();
    if (!supabase) return;
    const { error } = await supabase.from('deleted_records').delete()
      .eq('table_name', table).eq('record_id', String(recordId));
    if (error) console.error('[SupabaseSync] failed to roll back deletion marker:', error);
  }

"""
if "private async isRecordTombstoned(" not in s:
    marker = "  public async flushPendingSync() {"
    if marker not in s:
        raise RuntimeError("flushPendingSync anchor missing; cannot add durable deletion guard")
    s = s.replace(marker, helpers + marker, 1)

# Guard the lowest-level write path, including direct sales/ledger writes and pending queue retries.
if "isRecordTombstoned(table, recordId)" not in s:
    m = re.search(r"(?:public|private|protected)\s+async\s+rawUpsertRecord\s*\([^)]*\)\s*\{", s)
    if not m:
        raise RuntimeError("rawUpsertRecord method not found")
    insert_at = m.end()
    guard = """
    const tombstoneId = this.getRecordIdForTable(table, data);
    if (tombstoneId && await this.isRecordTombstoned(table, tombstoneId)) {
      this.clearPendingSyncForRecord(table, tombstoneId);
      console.warn('[SupabaseSync] skipped stale write for permanently deleted row', table, tombstoneId);
      return;
    }
"""
    s = s[:insert_at] + guard + s[insert_at:]

# Employee deletion: server tombstone first, actual row deletion must return the deleted row.
start = s.find("  public async deleteUserAccount(userId: string): Promise<boolean> {")
end = s.find("  public async syncOperationalPeriod(", start)
if start < 0 or end < 0:
    raise RuntimeError("deleteUserAccount method boundaries missing")
user_method = r"""  public async deleteUserAccount(userId: string): Promise<boolean> {
    const supabase = getSupabaseClient();
    if (!supabase || !userId) return false;
    let marked = false;
    try {
      await this.markRecordDeleted('users', userId);
      marked = true;
      const { data: deletedUsers, error } = await supabase
        .from('users').delete().eq('user_id', userId).select('user_id');
      if (error) throw error;
      if (!deletedUsers || deletedUsers.length === 0) {
        throw new Error('Akun tidak ditemukan di Supabase atau penghapusan ditolak oleh kebijakan akses.');
      }
      if (this.channel) {
        this.channel.send({ type: 'broadcast', event: 'tgp_mutation', payload: { type: 'DELETE', table: 'users', id: userId } });
      }
      return true;
    } catch (error) {
      if (marked) await this.unmarkRecordDeleted('users', userId);
      console.warn('[SupabaseSync] deleteUserAccount failed:', error);
      return false;
    }
  }

"""
s = s[:start] + user_method + s[end:]
sync.write_text(s)
print("Added durable tombstones, pending-queue purge, and verified employee deletion")

# Make the sale deletion atomically-ish tombstone the sale and all receipt-linked ledgers before deleting them.
s = sync.read_text()
start = s.find("  public async deleteSale(sale: SaleOrderEntity): Promise<boolean> {")
end = s.find("  public async deleteUserAccount(userId: string): Promise<boolean> {", start)
if start < 0 or end < 0:
    raise RuntimeError("deleteSale method boundaries missing")
sale_method = r"""  public async deleteSale(sale: SaleOrderEntity): Promise<boolean> {
    const supabase = getSupabaseClient();
    if (!supabase || !sale?.saleId || !sale?.businessId || !sale?.receiptNumber) return false;
    const markedIds: string[] = [];
    let linkedLedgers: any[] = [];
    let ledgersRemoved = false;
    try {
      const linkedReferences = [sale.receiptNumber, sale.saleId].filter(Boolean);
      const { data: ledgerRows, error: readLedgerError } = await supabase
        .from('ledgers').select('*')
        .eq('business_id', sale.businessId)
        .in('reference_id', linkedReferences);
      if (readLedgerError) throw readLedgerError;
      linkedLedgers = ledgerRows || [];

      await this.markRecordDeleted('sales', sale.saleId);
      markedIds.push(sale.saleId);
      for (const row of linkedLedgers) {
        if (row?.transaction_id) {
          await this.markRecordDeleted('ledgers', String(row.transaction_id));
          markedIds.push(String(row.transaction_id));
        }
      }

      const { error: ledgerError } = await supabase.from('ledgers').delete()
        .eq('business_id', sale.businessId)
        .in('reference_id', linkedReferences);
      if (ledgerError) throw ledgerError;
      ledgersRemoved = true;

      const { data: deletedSales, error: saleError } = await supabase
        .from('sales').delete().eq('sale_id', sale.saleId).select('sale_id');
      if (saleError) throw saleError;
      if (!deletedSales || deletedSales.length === 0) {
        throw new Error('Transaksi tidak ditemukan di Supabase atau penghapusan ditolak oleh kebijakan akses.');
      }

      if (this.channel) {
        this.channel.send({ type: 'broadcast', event: 'tgp_mutation', payload: { type: 'DELETE', table: 'sales', id: sale.saleId } });
        this.channel.send({ type: 'broadcast', event: 'tgp_mutation', payload: { type: 'DELETE', table: 'ledgers', id: sale.receiptNumber } });
      }
      return true;
    } catch (error) {
      console.warn('[SupabaseSync] deleteSale failed:', error);
      if (ledgersRemoved && linkedLedgers.length) {
        try {
          const { error: restoreError } = await supabase.from('ledgers').upsert(linkedLedgers);
          if (restoreError) console.error('[SupabaseSync] ledger rollback failed:', restoreError);
        } catch (restoreError) {
          console.error('[SupabaseSync] ledger rollback exception:', restoreError);
        }
      }
      for (const id of markedIds) await this.unmarkRecordDeleted(
        id === sale.saleId ? 'sales' : 'ledgers', id
      );
      return false;
    }
  }

"""
s = s[:start] + sale_method + s[end:]
sync.write_text(s)
print("Updated sale deletion to tombstone transaction and receipt-linked ledgers")
