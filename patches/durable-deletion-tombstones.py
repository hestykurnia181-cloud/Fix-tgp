from pathlib import Path
import re

ROOT = Path("project")
sync = ROOT / "src/services/supabaseSyncService.ts"
s = sync.read_text()
if "public lastSaleDeletionError" not in s:
    s = s.replace("class SupabaseSyncService {", "class SupabaseSyncService {\n  public lastSaleDeletionError = '';", 1)

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
    const tombstoneId = this.getRecordIdForTable(table, dbPayload);
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
    if (!supabase || !sale?.saleId) {
      this.lastSaleDeletionError = 'Supabase tidak tersedia atau ID transaksi kosong.';
      return false;
    }
    try {
      const { data, error } = await supabase.rpc('delete_pos_sale', {
        p_sale_id: String(sale.saleId),
        p_business_id: sale.businessId ? String(sale.businessId) : null,
        p_receipt_number: sale.receiptNumber ? String(sale.receiptNumber) : null,
      });
      if (error) throw error;
      if (!data || data.success !== true) throw new Error('Supabase tidak mengonfirmasi penghapusan transaksi.');
      this.clearPendingSyncForRecord('sales', String(sale.saleId));
      const deletedLedgerIds = Array.isArray(data.ledger_ids) ? data.ledger_ids : [];
      for (const ledgerId of deletedLedgerIds) this.clearPendingSyncForRecord('ledgers', String(ledgerId));
      this.lastSaleDeletionError = '';
      if (this.channel) {
        this.channel.send({ type: 'broadcast', event: 'tgp_mutation', payload: { type: 'DELETE', table: 'sales', id: sale.saleId } });
        this.channel.send({ type: 'broadcast', event: 'tgp_mutation', payload: { type: 'DELETE', table: 'ledgers', id: sale.receiptNumber } });
      }
      return true;
    } catch (error: any) {
      const details = [error?.message, error?.details, error?.hint, error?.code].filter((value) => value != null && String(value).trim() !== '').map((value) => String(value)).join(' | ');
      this.lastSaleDeletionError = details || 'Kesalahan Supabase tidak diketahui.';
      console.error('[SupabaseSync] deleteSale failed:', error);
      return false;
    }
  }

"""
s = s[:start] + sale_method + s[end:]
sync.write_text(s)
print("Updated sale deletion to use atomic database RPC")

# Block stale local snapshots from bypassing the low-level upsert tombstone guard.
s = sync.read_text()
old = "const missing=rows.map(mapper).filter((r:any)=>r && r[key]!=null && !existing.has(String(r[key])));"
new = """const missing:any[] = [];
        for (const row of rows) {
          const payload:any = mapper(row);
          const recordId = payload?.[key];
          if (recordId == null || existing.has(String(recordId))) continue;
          try {
            if (await this.isRecordTombstoned(table, String(recordId))) {
              this.clearPendingSyncForRecord(table, String(recordId));
              continue;
            }
          } catch (tombstoneError) {
            console.warn('[cross-device] tombstone check failed; skipped recovery insert', table, String(recordId), tombstoneError);
            continue;
          }
          missing.push(payload);
        }"""
if old not in s:
    raise RuntimeError("reconcileLocalSnapshot missing-row anchor not found")
s = s.replace(old, new, 1)
sync.write_text(s)

# Expose the actual Supabase error instead of hiding the cause behind a generic message.
context = ROOT / "src/context/TgpContext.tsx"
c = context.read_text()
old_message = "setErrorMessage('Transaksi gagal dihapus dari Supabase. Data lokal tidak diubah.');"
new_message = "setErrorMessage('Transaksi gagal dihapus dari Supabase: ' + (supabaseSyncService.lastSaleDeletionError || 'periksa koneksi dan izin database.'));"
if old_message not in c:
    raise RuntimeError("transaction deletion error message anchor not found")
context.write_text(c.replace(old_message, new_message, 1))
print("Guarded cross-device snapshot recovery and exposed deletion diagnostics")
