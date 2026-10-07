from pathlib import Path

ROOT = Path("project")

def replace_once(path, old, new, label):
    s = path.read_text()
    if old not in s:
        raise RuntimeError(label)
    path.write_text(s.replace(old, new, 1))

# ---------------------------------------------------------------------------
# 1) Cross-device recovery: merge records that were previously saved only in
#    a device's localStorage into Supabase, but NEVER overwrite an existing
#    server row. This makes the server the shared source of truth while
#    recovering old Device A/B/C/D data.
# ---------------------------------------------------------------------------
sync = ROOT / "src/services/supabaseSyncService.ts"
s = sync.read_text()

anchor = """  public async flushPendingSync() {
    if(typeof navigator!=='undefined' && !navigator.onLine) return;
    const rows=this.readPendingSync(); const keep:any[]=[];
    for(const row of rows) {
      try { await this.rawUpsertRecord(row.table,row.data); } catch { keep.push(row); }
    }
    this.writePendingSync(keep);
  }


"""
if anchor not in s:
    raise RuntimeError("flushPendingSync anchor not found")

reconcile = """  public async reconcileLocalSnapshot(snapshot: {
    businesses?: BusinessEntity[];
    users?: UserEntity[];
    items?: ItemEntity[];
    sales?: SaleOrderEntity[];
    ledgers?: LedgerTransactionEntity[];
    transfers?: TransferEntity[];
    damaged?: DamagedGoodsReportEntity[];
    attendances?: AttendanceEntity[];
    outlets?: OutletEntity[];
    outletStocks?: OutletStockEntity[];
    stanTransfers?: StanTransferEntity[];
    stockMutations?: StockMutationEntity[];
    auditLogs?: AuditLogEntity[];
    operationalPeriods?: OperationalPeriodEntity[];
  }) {
    const supabase = getSupabaseClient();
    if (!supabase) return;
    if (typeof navigator !== 'undefined' && !navigator.onLine) return;

    const configs: Array<{table:string; rows:any[]; key:string; map:(x:any)=>any}> = [
      {table:'businesses', rows:snapshot.businesses||[], key:'business_id', map:mapBusinessToDb},
      {table:'users', rows:snapshot.users||[], key:'user_id', map:mapUserToDb},
      {table:'items', rows:snapshot.items||[], key:'item_id', map:mapItemToDb},
      {table:'sales', rows:snapshot.sales||[], key:'sale_id', map:mapSaleToDb},
      {table:'ledgers', rows:snapshot.ledgers||[], key:'transaction_id', map:mapLedgerToDb},
      {table:'transfers', rows:snapshot.transfers||[], key:'transfer_id', map:mapTransferToDb},
      {table:'damaged_goods', rows:snapshot.damaged||[], key:'report_id', map:mapDamagedToDb},
      {table:'attendances', rows:snapshot.attendances||[], key:'attendance_id', map:mapAttendanceToDb},
      {table:'outlets', rows:snapshot.outlets||[], key:'outlet_id', map:mapOutletToDb},
      {table:'outlet_stocks', rows:snapshot.outletStocks||[], key:'stock_id', map:mapOutletStockToDb},
      {table:'stan_transfers', rows:snapshot.stanTransfers||[], key:'transfer_id', map:mapStanTransferToDb},
      {table:'stock_mutations', rows:snapshot.stockMutations||[], key:'mutation_id', map:mapStockMutationToDb},
      {table:'audit_logs', rows:snapshot.auditLogs||[], key:'log_id', map:mapAuditLogToDb},
      {table:'operational_periods', rows:snapshot.operationalPeriods||[], key:'period_id', map:mapOperationalPeriodToDb},
    ];

    for (const cfg of configs) {
      if (!cfg.rows.length) continue;
      try {
        const { data, error } = await supabase.from(cfg.table).select(cfg.key);
        if (error) {
          console.warn('[SupabaseSync] Reconcile read failed for '+cfg.table+':', error.message);
          continue;
        }
        const existing = new Set((data||[]).map((r:any)=>String(r[cfg.key])));
        const missing = cfg.rows
          .map(cfg.map)
          .filter((row:any)=>row && row[cfg.key] != null && !existing.has(String(row[cfg.key])));
        if (!missing.length) continue;
        const { error: upsertError } = await supabase.from(cfg.table).insert(missing);
        if (upsertError) {
          console.warn('[SupabaseSync] Reconcile insert failed for '+cfg.table+':', upsertError.message);
          for (const row of missing) this.queuePendingSync(cfg.table, row);
          continue;
        }
        if (this.channel) {
          this.channel.send({
            type:'broadcast',
            event:'tgp_mutation',
            payload:{type:'SNAPSHOT_RECOVERY', table:cfg.table, count:missing.length}
          });
        }
        console.log('[SupabaseSync] Recovered '+missing.length+' local records into '+cfg.table);
      } catch (error) {
        console.warn('[SupabaseSync] Reconcile exception for '+cfg.table+':', error);
      }
    }
  }


"""
s=s.replace(anchor,anchor+reconcile,1)

# Sales and ledgers are transactional and must not be treated as successful
# locally until Supabase confirms the write.
replace_once(sync,
"""  public async syncSale(sale: SaleOrderEntity) {
    await this.safeUpsertRecord('sales', mapSaleToDb(sale));
  }""",
"""  public async syncSale(sale: SaleOrderEntity) {
    await this.rawUpsertRecord('sales', mapSaleToDb(sale));
  }""",
"strict syncSale anchor not found")

replace_once(sync,
"""  public async syncLedger(ledger: LedgerTransactionEntity) {
    await this.safeUpsertRecord('ledgers', mapLedgerToDb(ledger));
  }""",
"""  public async syncLedger(ledger: LedgerTransactionEntity) {
    await this.rawUpsertRecord('ledgers', mapLedgerToDb(ledger));
  }""",
"strict syncLedger anchor not found")

# ---------------------------------------------------------------------------
# 2) Migrate the existing local snapshot once at app startup. Remote records
#    win when IDs already exist; only missing local IDs are inserted.
# ---------------------------------------------------------------------------
ctx = ROOT / "src/context/TgpContext.tsx"
c = ctx.read_text()

old_init = """    // Seed initial data if DB is empty
    supabaseSyncService.seedInitialData({
      businesses: INITIAL_BUSINESSES,
      users: INITIAL_USERS,
      items: INITIAL_ITEMS,
      ledgers: INITIAL_LEDGERS,
      sales: INITIAL_SALES,
      transfers: INITIAL_TRANSFERS,
      damaged: INITIAL_DAMAGED,
      auditLogs: INITIAL_AUDIT_LOGS,
    });"""
new_init = """    // Seed initial data if DB is empty, then recover any records that existed
    // only on this device before cross-device Supabase synchronization was fixed.
    void supabaseSyncService.seedInitialData({
      businesses: INITIAL_BUSINESSES,
      users: INITIAL_USERS,
      items: INITIAL_ITEMS,
      ledgers: INITIAL_LEDGERS,
      sales: INITIAL_SALES,
      transfers: INITIAL_TRANSFERS,
      damaged: INITIAL_DAMAGED,
      auditLogs: INITIAL_AUDIT_LOGS,
    }).then(() => supabaseSyncService.reconcileLocalSnapshot({
      businesses,
      users,
      items,
      sales,
      ledgers,
      transfers,
      damaged: damagedReports,
      attendances,
      outlets,
      outletStocks,
      stanTransfers,
      stockMutations,
      auditLogs,
      operationalPeriods,
    })).catch((error) => {
      console.warn('[TGP sync] Local snapshot recovery failed:', error);
    });"""
replace_once(ctx,old_init,new_init,"startup reconciliation anchor not found")

# Make checkout asynchronous so a sale is never reported successful when the
# Supabase write failed.
replace_once(ctx,
"""  ) => SaleOrderEntity | null;
""",
"""  ) => Promise<SaleOrderEntity | null>;
""",
"checkout context return type anchor not found")

replace_once(ctx,
"""  ) => SaleOrderEntity | null => {""",
"""  ): Promise<SaleOrderEntity | null> => {""",
"checkout implementation signature anchor not found")

# Put the Supabase confirmation BEFORE publishing the sale/ledger to local
# React state. The service-only flow therefore cannot create a phantom local
# transaction that another device can never see.
replace_once(ctx,
"""    setSales((prev) => [newSale, ...prev]);
    supabaseSyncService.syncSale(newSale);

    // 4. Record Ledger Entry (PEMASUKAN)""",
"""    try {
      await supabaseSyncService.syncSale(newSale);
    } catch (error:any) {
      setErrorMessage('Transaksi gagal disimpan ke server Supabase. Tidak ada transaksi lokal yang dianggap selesai. ' + (error?.message || 'Silakan coba lagi.'));
      return null;
    }
    setSales((prev) => [newSale, ...prev]);

    // 4. Record Ledger Entry (PEMASUKAN)""",
"sale sync ordering anchor not found")

replace_once(ctx,
"""    setLedgers((prev) => [newLedger, ...prev]);
    supabaseSyncService.syncLedger(newLedger);""",
"""    try {
      await supabaseSyncService.syncLedger(newLedger);
    } catch (error:any) {
      setErrorMessage('Transaksi tersimpan di server tetapi jurnal gagal disimpan. Silakan ulangi sinkronisasi. ' + (error?.message || ''));
      return null;
    }
    setLedgers((prev) => [newLedger, ...prev]);""",
"ledger sync ordering anchor not found")

ctx.write_text(c)

# ---------------------------------------------------------------------------
# 3) POS awaits the async checkout result.
# Verified against the current checkout signature in the source ZIP.
# ---------------------------------------------------------------------------
pos = ROOT / "src/screens/PosScreen.tsx"
p = pos.read_text()
replace_once(pos,
"""  const handleCheckoutSubmit = (e: React.FormEvent) => {""",
"""  const handleCheckoutSubmit = async (e: React.FormEvent) => {""",
"POS checkout handler anchor not found")
replace_once(pos,
"""    const sale = checkout(
""",
"""    const sale = await checkout(
""",
"POS checkout call anchor not found")
pos.write_text(p)

print("Cross-device source-of-truth + local snapshot recovery patch applied")
