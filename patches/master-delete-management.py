from pathlib import Path
root = Path("project")

def rep(path, old, new, label):
    p = root / path
    s = p.read_text()
    if new in s:
        print("already applied:", label)
        return
    if old not in s:
        raise RuntimeError("patch anchor missing: " + label)
    p.write_text(s.replace(old, new, 1))
    print("patched:", label)

rep("src/context/TgpContext.tsx",
    "if (!actor || normalizeUserRole(actor.role) !== UserRole.OWNER) {\n      setErrorMessage('Hanya OWNER yang dapat menghapus transaksi penjualan.');",
    "if (!actor || normalizeUserRole(actor.role) !== UserRole.MASTER) {\n      setErrorMessage('Hanya MASTER yang dapat menghapus transaksi penjualan.');",
    "transaction role")

p = root / "src/screens/OwnerDashboardScreen.tsx"
s = p.read_text()
start = s.find("      {/* Owner-only transaction management */}")
if start >= 0:
    end = s.find("      {/* Authorized Businesses List */}", start)
    if end < 0:
        raise RuntimeError("owner panel end anchor missing")
    p.write_text(s[:start] + s[end:])
    print("removed owner transaction panel")

rep("src/context/TgpContext.tsx",
    "  deleteOwnerSale: (saleId: string) => Promise<boolean>;\n",
    "  deleteOwnerSale: (saleId: string) => Promise<boolean>;\n  deleteMasterEmployee: (userId: string) => Promise<boolean>;\n",
    "employee action contract")

fn = '''  const deleteMasterEmployee = async (userId: string): Promise<boolean> => {
    const actor = currentSession?.user;
    if (!actor || normalizeUserRole(actor.role) !== UserRole.MASTER) {
      setErrorMessage('Hanya MASTER yang dapat menghapus akun karyawan.');
      return false;
    }
    const target = users.find((u) => u.userId === userId);
    if (!target || [UserRole.MASTER, UserRole.OWNER].includes(normalizeUserRole(target.role))) {
      setErrorMessage('Akun tidak ditemukan atau merupakan akun MASTER/OWNER.');
      return false;
    }
    const ok = await supabaseSyncService.deleteUserAccount(target.userId);
    if (!ok) {
      setErrorMessage('Akun gagal dihapus dari Supabase. Data lokal tidak diubah.');
      return false;
    }
    setUsers((prev) => prev.filter((u) => u.userId !== target.userId));
    addAuditLog('MASTER_DELETE_EMPLOYEE', 'MASTER ' + actor.username + ' menghapus akun karyawan ' + target.username + '.', target.businessId || undefined);
    setUserMessage('Akun karyawan ' + target.username + ' berhasil dihapus.');
    return true;
  };

'''
rep("src/context/TgpContext.tsx", "  const resetMasterAccount = () => {\n", fn + "  const resetMasterAccount = () => {\n", "employee action")
rep("src/context/TgpContext.tsx", "        deleteOwnerSale,\n", "        deleteOwnerSale,\n        deleteMasterEmployee,\n", "employee provider")

service = '''  public async deleteUserAccount(userId: string): Promise<boolean> {
    const supabase = getSupabaseClient();
    if (!supabase || !userId) return false;
    try {
      const { error } = await supabase.from('users').delete().eq('user_id', userId);
      if (error) throw error;
      if (this.channel) this.channel.send({ type: 'broadcast', event: 'tgp_mutation', payload: { type: 'INSERT_OR_UPDATE', table: 'users' } });
      return true;
    } catch (error) {
      console.warn('[SupabaseSync] deleteUserAccount failed:', error);
      return false;
    }
  }

'''
rep("src/services/supabaseSyncService.ts", "  public async syncOperationalPeriod(period: OperationalPeriodEntity) {\n", service + "  public async syncOperationalPeriod(period: OperationalPeriodEntity) {\n", "Supabase user removal service")

rep("src/screens/MasterDashboardScreen.tsx",
    "import {\n  Users,",
    "import {\n  Users,\n  Trash2,\n  ReceiptText,",
    "master icons")
rep("src/screens/MasterDashboardScreen.tsx",
    "    resetUserPassword,\n",
    "    resetUserPassword,\n    deleteMasterEmployee,\n    globalOwnerSales,\n    deleteOwnerSale,\n",
    "master actions")

p = root / "src/screens/MasterDashboardScreen.tsx"
s = p.read_text()
needle = "data-testid={`btn_user_details_${u.userId}`}"
i = s.find(needle)
if i < 0:
    raise RuntimeError("master account action anchor missing")
end = s.find("                    </button>", i) + len("                    </button>")
if end < len("                    </button>"):
    raise RuntimeError("master button end missing")
button = '''
                    {!['MASTER', 'OWNER'].includes(String(u.role).toUpperCase()) && (
                      <button type="button" onClick={async (e) => {
                        e.stopPropagation();
                        if (!window.confirm('Hapus akun karyawan ' + u.username + '? Tindakan ini tidak dapat dibatalkan.')) return;
                        const ok = await deleteMasterEmployee(u.userId);
                        if (ok && selectedUser?.userId === u.userId) setSelectedUser(null);
                        if (ok) window.alert('Akun karyawan berhasil dihapus.');
                      }} className="px-3 py-1.5 rounded-lg bg-rose-600 text-white text-[11px] font-bold inline-flex items-center gap-1"
                        data-testid={"btn_master_delete_employee_" + u.userId}>
                        <Trash2 className="w-3.5 h-3.5" /> Hapus
                      </button>
                    )}'''
if "btn_master_delete_employee_" not in s:
    s = s[:end] + button + s[end:]
    p.write_text(s)

p = root / "src/screens/MasterDashboardScreen.tsx"
s = p.read_text()
if "data-testid={'btn_master_delete_sale_' + sale.saleId}" not in s:
    panel = '''      <section className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div><h3 className="text-base font-extrabold text-slate-900 flex items-center gap-2"><ReceiptText className="w-4 h-4 text-indigo-600" /> Riwayat Transaksi Penjualan</h3>
          <p className="text-xs text-slate-500">Penghapusan hanya tersedia untuk MASTER. Jurnal penjualan terkait ikut dihapus.</p></div>
          <span className="text-[11px] font-bold text-slate-500">{globalOwnerSales.length} transaksi</span>
        </div>
        <div className="space-y-2 max-h-[520px] overflow-y-auto">
          {[...globalOwnerSales].sort((a,b) => b.timestamp-a.timestamp).map((sale) => (
            <div key={sale.saleId} className="p-3 rounded-2xl border border-slate-100 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div><p className="text-xs font-extrabold">{sale.receiptNumber}</p><p className="text-[10px] text-slate-500">{sale.businessName || 'Bisnis'} · {sale.cashierName} · {new Date(sale.timestamp).toLocaleString('id-ID')}</p><p className="text-xs font-extrabold text-emerald-700">{formatRupiah(sale.totalAmount)}</p></div>
              <button type="button" onClick={async () => {
                if (!window.confirm('Hapus transaksi ' + sale.receiptNumber + ' senilai ' + formatRupiah(sale.totalAmount) + '? Jurnal terkait juga dihapus dan stok dikembalikan jika didukung.')) return;
                const ok = await deleteOwnerSale(sale.saleId);
                if (ok) window.alert('Transaksi berhasil dihapus.');
              }} className="px-3 py-2 rounded-xl bg-rose-600 text-white text-[11px] font-extrabold inline-flex items-center gap-1.5" data-testid={'btn_master_delete_sale_' + sale.saleId}>
                <Trash2 className="w-3.5 h-3.5" /> Hapus Transaksi
              </button>
            </div>
          ))}
          {globalOwnerSales.length === 0 && <p className="py-6 text-center text-xs text-slate-400">Belum ada transaksi.</p>}
        </div>
      </section>

'''
    anchor = "      <CreateBusinessDialog\n"
    if anchor not in s: raise RuntimeError("master panel insertion anchor missing")
    p.write_text(s.replace(anchor, panel + anchor, 1))

print("Master transaction and employee management patch complete")
