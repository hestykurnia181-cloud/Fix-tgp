from pathlib import Path

ROOT = Path("project")

def patch(path, old, new, label):
    s = path.read_text()
    if new in s:
        print("[cross-device] already applied:", label)
        return
    if old in s:
        path.write_text(s.replace(old, new, 1))
        print("[cross-device] applied:", label)
    else:
        print("[cross-device] anchor not found, skipped:", label)

sync = ROOT / "src/services/supabaseSyncService.ts"
ctx = ROOT / "src/context/TgpContext.tsx"
pos = ROOT / "src/screens/PosScreen.tsx"

# Recover records that exist on a device but are missing from the shared server.
# Existing server IDs are never overwritten by this recovery pass.
s = sync.read_text()
if "public async reconcileLocalSnapshot(" not in s:
    marker = """  public async flushPendingSync() {
    if(typeof navigator!=='undefined' && !navigator.onLine) return;
    const rows=this.readPendingSync(); const keep:any[]=[];
    for(const row of rows) {
      try { await this.rawUpsertRecord(row.table,row.data); } catch { keep.push(row); }
    }
    this.writePendingSync(keep);
  }


"""
    method = """  public async reconcileLocalSnapshot(snapshot: {
    businesses?: BusinessEntity[]; users?: UserEntity[]; items?: ItemEntity[];
    sales?: SaleOrderEntity[]; ledgers?: LedgerTransactionEntity[];
    transfers?: TransferEntity[]; damaged?: DamagedGoodsReportEntity[];
    attendances?: AttendanceEntity[]; outlets?: OutletEntity[];
    outletStocks?: OutletStockEntity[]; stanTransfers?: StanTransferEntity[];
    stockMutations?: StockMutationEntity[]; auditLogs?: AuditLogEntity[];
    operationalPeriods?: OperationalPeriodEntity[];
  }) {
    const supabase = getSupabaseClient();
    if (!supabase || (typeof navigator !== 'undefined' && !navigator.onLine)) return;
    const configs:any[] = [
      ['businesses',snapshot.businesses||[],'business_id',mapBusinessToDb],
      ['users',snapshot.users||[],'user_id',mapUserToDb],
      ['items',snapshot.items||[],'item_id',mapItemToDb],
      ['sales',snapshot.sales||[],'sale_id',mapSaleToDb],
      ['ledgers',snapshot.ledgers||[],'transaction_id',mapLedgerToDb],
      ['transfers',snapshot.transfers||[],'transfer_id',mapTransferToDb],
      ['damaged_goods',snapshot.damaged||[],'report_id',mapDamagedToDb],
      ['attendances',snapshot.attendances||[],'attendance_id',mapAttendanceToDb],
      ['outlets',snapshot.outlets||[],'outlet_id',mapOutletToDb],
      ['outlet_stocks',snapshot.outletStocks||[],'stock_id',mapOutletStockToDb],
      ['stan_transfers',snapshot.stanTransfers||[],'transfer_id',mapStanTransferToDb],
      ['stock_mutations',snapshot.stockMutations||[],'mutation_id',mapStockMutationToDb],
      ['audit_logs',snapshot.auditLogs||[],'log_id',mapAuditLogToDb],
      ['operational_periods',snapshot.operationalPeriods||[],'period_id',mapOperationalPeriodToDb],
    ];
    for (const [table,rows,key,mapper] of configs) {
      if (!rows.length) continue;
      try {
        const {data,error}=await supabase.from(table).select(key);
        if (error) { console.warn('[cross-device] read failed',table,error.message); continue; }
        const existing=new Set((data||[]).map((r:any)=>String(r[key])));
        const missing=rows.map(mapper).filter((r:any)=>r && r[key]!=null && !existing.has(String(r[key])));
        if (!missing.length) continue;
        const {error:insertError}=await supabase.from(table).insert(missing);
        if (insertError) {
          console.warn('[cross-device] recovery insert failed',table,insertError.message);
          for (const row of missing) this.queuePendingSync(table,row);
        } else {
          console.log('[cross-device] recovered',missing.length,'records into',table);
        }
      } catch (e) { console.warn('[cross-device] recovery exception',table,e); }
    }
  }


"""
    if marker in s:
        sync.write_text(s.replace(marker,marker+method,1))
        print("[cross-device] applied: local snapshot recovery")
    else:
        print("[cross-device] recovery marker not found")

s = sync.read_text()
patch(sync,
"""  public async syncSale(sale: SaleOrderEntity) {
    await this.safeUpsertRecord('sales', mapSaleToDb(sale));
  }""",
"""  public async syncSale(sale: SaleOrderEntity) {
    await this.rawUpsertRecord('sales', mapSaleToDb(sale));
  }""","strict sales write")
patch(sync,
"""  public async syncLedger(ledger: LedgerTransactionEntity) {
    await this.safeUpsertRecord('ledgers', mapLedgerToDb(ledger));
  }""",
"""  public async syncLedger(ledger: LedgerTransactionEntity) {
    await this.rawUpsertRecord('ledgers', mapLedgerToDb(ledger));
  }""","strict ledger write")

patch(ctx,
"""    // Seed initial data if DB is empty
    supabaseSyncService.seedInitialData({
      businesses: INITIAL_BUSINESSES,
      users: INITIAL_USERS,
      items: INITIAL_ITEMS,
      ledgers: INITIAL_LEDGERS,
      sales: INITIAL_SALES,
      transfers: INITIAL_TRANSFERS,
      damaged: INITIAL_DAMAGED,
      auditLogs: INITIAL_AUDIT_LOGS,
    });""",
"""    // Seed initial data if DB is empty, then recover local records missing on the server.
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
      businesses: loadStored('businesses', INITIAL_BUSINESSES),
      users: loadStored('users', INITIAL_USERS),
      items: loadStored('items', INITIAL_ITEMS),
      sales: loadStored('sales', INITIAL_SALES),
      ledgers: loadStored('ledgers', INITIAL_LEDGERS),
      transfers: loadStored('transfers', INITIAL_TRANSFERS),
      damaged: loadStored('damaged', INITIAL_DAMAGED),
      attendances: loadStored('attendances', []),
      outlets: loadStored('outlets', []),
      outletStocks: loadStored('outlet_stocks', []),
      stanTransfers: loadStored('stan_transfers', []),
      stockMutations: loadStored('mutations', []),
      auditLogs: loadStored('audit', INITIAL_AUDIT_LOGS),
      operationalPeriods: loadStored('operational_periods', []),
    })).catch((error) => console.warn('[cross-device] local recovery failed', error));""",
"startup local recovery")

patch(ctx,
"""  ) => SaleOrderEntity | null;""",
"""  ) => Promise<SaleOrderEntity | null>;""","async checkout contract")
patch(ctx,
"""  ): SaleOrderEntity | null => {""",
"""  ): Promise<SaleOrderEntity | null => {""","async checkout implementation")

patch(ctx,
"""    setSales((prev) => [newSale, ...prev]);
    supabaseSyncService.syncSale(newSale);

    // 4. Record Ledger Entry (PEMASUKAN)""",
"""    try {
      await supabaseSyncService.syncSale(newSale);
    } catch (error:any) {
      setErrorMessage('Transaksi gagal disimpan ke server Supabase. Transaksi dibatalkan: ' + (error?.message || ''));
      return null;
    }
    setSales((prev) => [newSale, ...prev]);

    // 4. Record Ledger Entry (PEMASUKAN)""","confirmed sales write before local commit")

patch(ctx,
"""    setLedgers((prev) => [newLedger, ...prev]);
    supabaseSyncService.syncLedger(newLedger);""",
"""    try {
      await supabaseSyncService.syncLedger(newLedger);
    } catch (error:any) {
      setErrorMessage('Jurnal transaksi gagal disimpan ke server Supabase: ' + (error?.message || ''));
      return null;
    }
    setLedgers((prev) => [newLedger, ...prev]);""","confirmed ledger write before local commit")

patch(pos,
"""  const handleCheckoutSubmit = async (e: React.FormEvent) => {""",
"""  const handleCheckoutSubmit = (e: React.FormEvent) => {""","sync POS checkout handler")

patch(pos,
"""    const sale = await checkout(
""",
"""    void checkout(
""","fire-and-forget promise explicitly void")

# Convert the Promise result into the same success UI without making the
# React form onSubmit callback itself async.
patch(pos,
"""    if (sale) {
      setIsCheckoutOpen(false);
      setCustomerName('');
      setNominalReceived('');
      setDiscountType('NONE');
      setDiscountValueInput('');
      setDiscountNote('');
      setIsDiscountOpen(false);
      setCompletedSale(sale);
    }""",
"""    ).then((sale) => {
      if (sale) {
        setIsCheckoutOpen(false);
        setCustomerName('');
        setNominalReceived('');
        setDiscountType('NONE');
        setDiscountValueInput('');
        setDiscountNote('');
        setIsDiscountOpen(false);
        setCompletedSale(sale);
      }
    });""","handle async checkout result")


print("[cross-device] patch completed")
