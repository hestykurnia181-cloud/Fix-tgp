from pathlib import Path
p = Path("project/src/screens/ReportsScreen.tsx")
s = p.read_text(encoding="utf-8")
old = """    activeBusinessFinance,
    canAccessFinance,
    canViewSalesReport,
    currentSession,
  } = useTgp();"""
new = """    activeBusinessFinance,
    periodLedgers,
    activeOutlets,
    canAccessFinance,
    canViewSalesReport,
    currentSession,
  } = useTgp();"""
assert s.count(old) == 1, "ReportsScreen context anchor mismatch"
s = s.replace(old, new)
old = """  const totalSalesRevenue = filteredSales.reduce((sum, sale) => sum + Number(sale.totalAmount || 0), 0);

  const bestSellers = useMemo(() => {"""
new = """  const totalSalesRevenue = filteredSales.reduce((sum, sale) => sum + Number(sale.totalAmount || 0), 0);

  // Group ledger entries by their own STAN and apply the selected report period.
  const filteredStanLedgers = useMemo(() => {
    const now = new Date();
    const todayStart = new Date(now); todayStart.setHours(0, 0, 0, 0);
    const weekStart = startOfWeek(now);
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    return periodLedgers.filter((entry) => {
      if (entry.businessId !== activeBusiness?.businessId || !entry.outletId) return false;
      if (isCashier && entry.outletId !== currentSession?.user.outletId) return false;
      const time = Number(entry.timestamp || entry.date || 0);
      if (!time) return false;
      if (dateFilter === 'ALL') return true;
      if (dateFilter === 'TODAY') return time >= todayStart.getTime();
      if (dateFilter === 'WEEK') return time >= weekStart.getTime();
      return time >= monthStart.getTime();
    });
  }, [periodLedgers, activeBusiness?.businessId, isCashier, currentSession?.user.outletId, dateFilter]);

  const stanFinancialRows = useMemo(() => activeOutlets
    .filter((outlet) => !isCashier || outlet.outletId === currentSession?.user.outletId)
    .map((outlet) => {
      const entries = filteredStanLedgers.filter((entry) => entry.outletId === outlet.outletId);
      const income = entries.filter((entry) => entry.type === 'PEMASUKAN').reduce((sum, entry) => sum + Number(entry.amount || 0), 0);
      const expense = entries.filter((entry) => entry.type === 'PENGELUARAN').reduce((sum, entry) => sum + Number(entry.amount || 0), 0);
      return { outletId: outlet.outletId, name: outlet.name, income, expense, net: income - expense };
    })
    .sort((a, b) => b.net - a.net), [activeOutlets, filteredStanLedgers, isCashier, currentSession?.user.outletId]);

  const stanIncomeTotal = stanFinancialRows.reduce((sum, row) => sum + row.income, 0);
  const stanExpenseTotal = stanFinancialRows.reduce((sum, row) => sum + row.expense, 0);
  const stanNetTotal = stanIncomeTotal - stanExpenseTotal;
  const stanChartMax = Math.max(1, ...stanFinancialRows.flatMap((row) => [row.income, row.expense]));

  const bestSellers = useMemo(() => {"""
assert s.count(old) == 1, "ReportsScreen total sales anchor mismatch"
s = s.replace(old, new)
old = """      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">"""
new = """      <section className="bg-white rounded-3xl p-5 border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex items-center justify-between gap-3"><div><h3 className="text-sm font-extrabold">Diagram Keuangan per STAN</h3><p className="text-xs text-slate-500 mt-1">Pemasukan dikurangi pengeluaran pada STAN yang sama · {periodLabel}</p></div><DollarSign className="w-5 h-5 text-emerald-600" /></div>
        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-2xl bg-emerald-50 p-3"><p className="text-[10px] font-bold text-emerald-700">Pemasukan</p><p className="text-sm sm:text-base font-black text-emerald-800">{formatRupiah(stanIncomeTotal)}</p></div>
          <div className="rounded-2xl bg-rose-50 p-3"><p className="text-[10px] font-bold text-rose-700">Pengeluaran</p><p className="text-sm sm:text-base font-black text-rose-800">{formatRupiah(stanExpenseTotal)}</p></div>
          <div className="rounded-2xl bg-blue-50 p-3"><p className="text-[10px] font-bold text-blue-700">Sisa Bersih</p><p className="text-sm sm:text-base font-black text-blue-800">{formatRupiah(stanNetTotal)}</p></div>
        </div>
        {stanFinancialRows.length ? <div className="space-y-4">{stanFinancialRows.map((row) => <div key={row.outletId} className="space-y-2">
          <div className="flex items-center justify-between gap-3"><span className="text-xs font-extrabold truncate">{row.name}</span><span className={`text-xs font-black ${row.net < 0 ? 'text-rose-600' : 'text-blue-700'}`}>{formatRupiah(row.net)}</span></div>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2"><span className="w-20 shrink-0 text-[10px] font-semibold text-slate-500">Pemasukan</span><div className="h-2.5 flex-1 rounded-full bg-slate-100 overflow-hidden"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.max(0, row.income) / stanChartMax * 100}%` }} /></div><span className="w-24 text-right text-[10px] font-bold">{formatRupiah(row.income)}</span></div>
            <div className="flex items-center gap-2"><span className="w-20 shrink-0 text-[10px] font-semibold text-slate-500">Pengeluaran</span><div className="h-2.5 flex-1 rounded-full bg-slate-100 overflow-hidden"><div className="h-full rounded-full bg-rose-500" style={{ width: `${Math.max(0, row.expense) / stanChartMax * 100}%` }} /></div><span className="w-24 text-right text-[10px] font-bold">{formatRupiah(row.expense)}</span></div>
          </div>
        </div>)}</div> : <p className="py-5 text-center text-xs text-slate-400">Belum ada data pemasukan atau pengeluaran STAN pada periode ini.</p>}
        <div className="flex flex-wrap gap-4 border-t border-slate-100 pt-3 text-[10px] font-semibold text-slate-500"><span className="flex items-center gap-1.5"><i className="w-2.5 h-2.5 rounded-full bg-emerald-500"/>Pemasukan</span><span className="flex items-center gap-1.5"><i className="w-2.5 h-2.5 rounded-full bg-rose-500"/>Pengeluaran</span></div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">"""
assert s.count(old) == 1, "ReportsScreen chart insertion anchor mismatch"
s = s.replace(old, new)
p.write_text(s, encoding="utf-8")
print("STAN net report and chart applied")
