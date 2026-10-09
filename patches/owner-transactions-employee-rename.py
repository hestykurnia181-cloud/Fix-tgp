from pathlib import Path
ROOT = Path("project")

def replace(path, old, new, label):
    p = ROOT / path
    s = p.read_text()
    if new in s:
        print("[owner-employee] already applied:", label)
        return
    if old not in s:
        raise RuntimeError("[owner-employee] anchor not found: " + label + " (" + path + ")")
    p.write_text(s.replace(old, new, 1))

replace("src/context/TgpContext.tsx",
"  resetUserPassword: (userId: string, newPassword: string, confirmPassword: string) => Promise<boolean>;\n",
"  resetUserPassword: (userId: string, newPassword: string, confirmPassword: string) => Promise<boolean>;\n  updateEmployeeName: (userId: string, fullName: string) => Promise<boolean>;\n  deleteOwnerSale: (saleId: string) => Promise<boolean>;\n", "context contracts")

methods = r'''  const updateEmployeeName = async (userId: string, fullName: string): Promise<boolean> => {
    const actor = currentSession?.user;
    const actorRole = actor ? normalizeUserRole(actor.role) : null;
    if (!actor || ![UserRole.OWNER, UserRole.ADMIN_OWNER, UserRole.ADMIN_DIVISI].includes(actorRole as UserRole)) {
      setErrorMessage('Anda tidak memiliki akses untuk mengganti nama karyawan.');
      return false;
    }
    const target = users.find((u) => u.userId === userId);
    if (!target || [UserRole.MASTER, UserRole.OWNER].includes(normalizeUserRole(target.role))) {
      setErrorMessage('Akun karyawan tidak ditemukan atau tidak dapat diubah dari menu ini.');
      return false;
    }
    const nextName = fullName.trim();
    if (nextName.length < 2) {
      setErrorMessage('Nama karyawan minimal 2 karakter.');
      return false;
    }
    const actorBusinessIds = new Set<string>([
      ...(actor.assignedBusinessIds || []),
      ...(actor.businessId ? [actor.businessId] : []),
      ...(actorRole === UserRole.OWNER ? authorizedBusinesses.map((b) => b.businessId) : []),
    ]);
    const targetBusinessIds = new Set<string>([
      ...(target.assignedBusinessIds || []),
      ...(target.businessId ? [target.businessId] : []),
    ]);
    if (![...actorBusinessIds].some((id) => targetBusinessIds.has(id))) {
      setErrorMessage('Anda hanya dapat mengganti nama karyawan pada bisnis yang menjadi akses Anda.');
      return false;
    }
    if (actorRole === UserRole.ADMIN_DIVISI &&
        [UserRole.ADMIN_OWNER, UserRole.ADMIN_DIVISI].includes(normalizeUserRole(target.role))) {
      setErrorMessage('Admin Divisi hanya dapat mengganti nama karyawan operasional.');
      return false;
    }
    const updatedUser: UserEntity = { ...target, fullName: nextName };
    try {
      const synced = await supabaseSyncService.syncUser(updatedUser);
      if (!synced) {
        setErrorMessage('Nama karyawan gagal disimpan ke Supabase.');
        return false;
      }
    } catch (error: any) {
      setErrorMessage('Nama karyawan gagal disimpan: ' + (error?.message || 'Error tidak diketahui'));
      return false;
    }
    setUsers((prev) => prev.map((u) => u.userId === userId ? updatedUser : u));
    addAuditLog('EMPLOYEE_NAME_CHANGED', actor.username + ' mengganti nama akun ' + target.username + ' menjadi ' + nextName + '.', target.businessId || undefined);
    setUserMessage('Nama karyawan ' + target.username + ' berhasil diubah menjadi ' + nextName + '.');
    return true;
  };

  const deleteOwnerSale = async (saleId: string): Promise<boolean> => {
    const actor = currentSession?.user;
    if (!actor || normalizeUserRole(actor.role) !== UserRole.OWNER) {
      setErrorMessage('Hanya OWNER yang dapat menghapus transaksi penjualan.');
      return false;
    }
    const target = sales.find((sale) => sale.saleId === saleId);
    if (!target || !authorizedBusinesses.some((biz) => biz.businessId === target.businessId)) {
      setErrorMessage('Transaksi tidak ditemukan atau berada di luar akses bisnis Anda.');
      return false;
    }
    const ok = await supabaseSyncService.deleteSale(target);
    if (!ok) {
      setErrorMessage('Transaksi gagal dihapus dari Supabase. Data lokal tidak diubah.');
      return false;
    }
    const changedAt = Date.now();
    if (target.outletId) {
      const changedStocks: OutletStockEntity[] = [];
      setOutletStocks((prev) => prev.map((stock) => {
        if (stock.outletId !== target.outletId || stock.businessId !== target.businessId) return stock;
        const line = (target.items || []).find((item) => item.itemId === stock.itemId);
        const item = items.find((entry) => entry.itemId === stock.itemId);
        if (!line || item?.type === 'SERVICE') return stock;
        const updated = { ...stock, stockQuantity: stock.stockQuantity + line.quantity, updatedAt: changedAt };
        changedStocks.push(updated);
        return updated;
      }));
      if (changedStocks.length) await supabaseSyncService.syncOutletStocks(changedStocks);
    } else {
      const changedItems: ItemEntity[] = [];
      setItems((prev) => prev.map((item) => {
        const line = (target.items || []).find((saleItem) => saleItem.itemId === item.itemId);
        if (!line || item.businessId !== target.businessId || item.type === 'SERVICE') return item;
        const updated = { ...item, stockQuantity: item.stockQuantity + line.quantity, updatedAt: changedAt };
        changedItems.push(updated);
        return updated;
      }));
      if (changedItems.length) await supabaseSyncService.syncItems(changedItems);
    }
    setSales((prev) => prev.filter((sale) => sale.saleId !== target.saleId));
    setLedgers((prev) => prev.filter((ledger) =>
      !(ledger.businessId === target.businessId && ledger.referenceId === target.receiptNumber && ledger.category === 'PENJUALAN_POS')
    ));
    addAuditLog('OWNER_DELETE_SALE', 'OWNER ' + actor.username + ' menghapus transaksi ' + target.receiptNumber + ' sebesar Rp ' + target.totalAmount.toLocaleString('id-ID') + '.', target.businessId);
    setUserMessage('Transaksi ' + target.receiptNumber + ' berhasil dihapus.');
    return true;
  };

'''
replace("src/context/TgpContext.tsx", "  const resetMasterAccount = () => {\n", methods + "  const resetMasterAccount = () => {\n", "context action implementations")
replace("src/context/TgpContext.tsx", "        resetUserPassword,\n", "        resetUserPassword,\n        updateEmployeeName,\n        deleteOwnerSale,\n", "context provider actions")

delete_method = r'''  public async deleteSale(sale: SaleOrderEntity): Promise<boolean> {
    const supabase = getSupabaseClient();
    if (!supabase) return false;
    try {
      const { error: readLedgerError } = await supabase
        .from('ledgers').select('transaction_id')
        .eq('business_id', sale.businessId)
        .eq('reference_id', sale.receiptNumber)
        .eq('category', 'PENJUALAN_POS');
      if (readLedgerError) throw readLedgerError;
      const { error: saleError } = await supabase.from('sales').delete().eq('sale_id', sale.saleId);
      if (saleError) throw saleError;
      const { error: ledgerError } = await supabase.from('ledgers').delete()
        .eq('business_id', sale.businessId)
        .eq('reference_id', sale.receiptNumber)
        .eq('category', 'PENJUALAN_POS');
      if (ledgerError) {
        await supabase.from('sales').upsert(mapSaleToDb(sale));
        throw ledgerError;
      }
      if (this.channel) {
        this.channel.send({ type: 'broadcast', event: 'tgp_mutation', payload: { type: 'INSERT_OR_UPDATE', table: 'sales' } });
        this.channel.send({ type: 'broadcast', event: 'tgp_mutation', payload: { type: 'INSERT_OR_UPDATE', table: 'ledgers' } });
      }
      return true;
    } catch (error) {
      console.warn('[SupabaseSync] deleteSale failed:', error);
      return false;
    }
  }

'''
replace("src/services/supabaseSyncService.ts", "  public async syncOperationalPeriod(period: OperationalPeriodEntity) {\n", delete_method + "  public async syncOperationalPeriod(period: OperationalPeriodEntity) {\n", "Supabase sale deletion")

replace("src/screens/EmployeeManagementScreen.tsx",
"import { CalendarCheck, Plus, Users, UserPlus, Clock3, ShieldCheck, KeyRound } from 'lucide-react';",
"import { CalendarCheck, Plus, Users, UserPlus, Clock3, ShieldCheck, KeyRound, Pencil } from 'lucide-react';",
"employee edit icon")
replace("src/screens/EmployeeManagementScreen.tsx",
"    resetUserPassword,\n    userMessage,",
"    resetUserPassword,\n    updateEmployeeName,\n    userMessage,",
"employee context action")
rename_button = r'''                      {canView && (
                        <button
                          type="button"
                          onClick={async (e) => {
                            e.stopPropagation();
                            const nextName = window.prompt('Nama baru untuk ' + u.username + ':', u.fullName);
                            if (nextName === null || nextName.trim() === u.fullName.trim()) return;
                            const ok = await updateEmployeeName(u.userId, nextName);
                            if (ok) window.alert('Nama karyawan berhasil diperbarui.');
                          }}
                          className="px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[10px] font-extrabold inline-flex items-center gap-1"
                          data-testid={"btn_rename_employee_" + u.userId}
                        >
                          <Pencil className="w-3.5 h-3.5" />
                          Ganti Nama
                        </button>
                      )}
                      {canManage && (role === UserRole.ADMIN_OWNER
                        ? [UserRole.STAFF, UserRole.KASIR, UserRole.WAREHOUSE, UserRole.ADMIN_DIVISI, UserRole.MANAGER].includes(u.role as UserRole)
                        : [UserRole.STAFF, UserRole.KASIR, UserRole.WAREHOUSE, UserRole.MANAGER].includes(u.role as UserRole)) && (
                        <button
                          type="button"
                          onClick={async (e) => {'''
employee_anchor = '''                      {canManage && (role === UserRole.ADMIN_OWNER
                        ? [UserRole.STAFF, UserRole.KASIR, UserRole.WAREHOUSE, UserRole.ADMIN_DIVISI, UserRole.MANAGER].includes(u.role as UserRole)
                        : [UserRole.STAFF, UserRole.KASIR, UserRole.WAREHOUSE, UserRole.MANAGER].includes(u.role as UserRole)) && (
                        <button
                          type="button"
                          onClick={async (e) => {'''
replace("src/screens/EmployeeManagementScreen.tsx", employee_anchor, rename_button, "employee rename button")

replace("src/screens/OwnerDashboardScreen.tsx", "  BadgeCheck,\n", "  BadgeCheck,\n  Trash2,\n  ReceiptText,\n", "owner transaction icons")
replace("src/screens/OwnerDashboardScreen.tsx", "    ownerFinanceSummary,\n", "    ownerFinanceSummary,\n    globalOwnerSales,\n    deleteOwnerSale,\n", "owner transaction actions")

owner_panel = r'''      {/* Owner-only transaction management */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-extrabold text-slate-900 flex items-center gap-2"><ReceiptText className="w-4 h-4 text-indigo-600" /> Kelola Transaksi Penjualan</h3>
            <p className="text-xs text-slate-500">OWNER dapat menghapus transaksi dan jurnal penjualan terkait. Penghapusan juga mengembalikan stok barang.</p>
          </div>
          <span className="text-[11px] font-bold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full shrink-0">{globalOwnerSales.length} transaksi</span>
        </div>
        <div className="space-y-2 max-h-[560px] overflow-y-auto pr-1">
          {globalOwnerSales.length === 0 ? (
            <p className="py-7 text-center text-xs text-slate-400">Belum ada transaksi penjualan.</p>
          ) : [...globalOwnerSales].sort((a, b) => b.timestamp - a.timestamp).map((sale) => (
            <div key={sale.saleId} className="p-3.5 rounded-2xl border border-slate-100 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3" data-testid={'owner_sale_' + sale.saleId}>
              <div className="min-w-0">
                <p className="text-xs font-extrabold text-slate-900 break-all">{sale.receiptNumber}</p>
                <p className="text-[10px] text-slate-500 mt-1">{sale.businessName || authorizedBusinesses.find((b) => b.businessId === sale.businessId)?.name || 'Bisnis'} · {sale.cashierName} · {new Date(sale.timestamp).toLocaleString('id-ID')}</p>
                <p className="text-xs font-extrabold text-emerald-700 mt-1">{formatRupiah(sale.totalAmount)}</p>
                <p className="text-[10px] text-slate-500 mt-1 line-clamp-2">{sale.itemsSummary}</p>
              </div>
              <button
                type="button"
                onClick={async () => {
                  const confirmed = window.confirm('Hapus transaksi ' + sale.receiptNumber + ' senilai ' + formatRupiah(sale.totalAmount) + '? Jurnal penjualan terkait juga dihapus dan stok barang dikembalikan. Tindakan ini tidak dapat dibatalkan.');
                  if (!confirmed) return;
                  const ok = await deleteOwnerSale(sale.saleId);
                  if (ok) window.alert('Transaksi ' + sale.receiptNumber + ' berhasil dihapus.');
                }}
                className="shrink-0 px-3 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-extrabold inline-flex items-center justify-center gap-1.5"
                data-testid={'btn_owner_delete_sale_' + sale.saleId}
              >
                <Trash2 className="w-3.5 h-3.5" /> Hapus Transaksi
              </button>
            </div>
          ))}
        </div>
      </div>

'''
replace("src/screens/OwnerDashboardScreen.tsx", "      {/* Authorized Businesses List */}\n", owner_panel + "      {/* Authorized Businesses List */}\n", "owner transaction panel")

print("Owner transaction deletion and employee rename patch applied.")
