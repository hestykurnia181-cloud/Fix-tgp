from pathlib import Path

ROOT = Path('project')
SEKAP_BUNGO_ID = 'biz-1790060286099'

def replace_once(path, old, new, label):
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if new in s:
        return
    if old not in s:
        raise SystemExit(f'Missing required anchor ({label}) in {path}')
    p.write_text(s.replace(old, new, 1), encoding='utf-8')

# Finance summary: change the income source ONLY for Sekap Bungo.
replace_once(
    'src/context/TgpContext.tsx',
    """  const activeBusinessFinance = {
    totalIncome: periodLedgers
      .filter((l) => l.type === LedgerType.PEMASUKAN)
      .reduce((sum, l) => sum + l.amount, 0),
    totalExpense: periodLedgers
      .filter((l) => l.type === LedgerType.PENGELUARAN)
      .reduce((sum, l) => sum + l.amount, 0),
    get netBalance() {
      return this.totalIncome - this.totalExpense;
    },
  };""",
    """  const isSekapBungoFinance = activeBusiness?.businessId === 'biz-1790060286099';
  const activeStanOutletIds = new Set(activeOutlets.map((outlet) => outlet.outletId));
  const activeStanSales = periodSales.filter(
    (sale) => !!sale.outletId && activeStanOutletIds.has(sale.outletId)
  );
  const activeBusinessFinance = {
    totalIncome: isSekapBungoFinance
      ? activeStanSales.reduce((sum, sale) => sum + Number(sale.totalAmount || 0), 0)
      : periodLedgers
          .filter((l) => l.type === LedgerType.PEMASUKAN)
          .reduce((sum, l) => sum + l.amount, 0),
    totalExpense: periodLedgers
      .filter((l) => l.type === LedgerType.PENGELUARAN)
      .reduce((sum, l) => sum + l.amount, 0),
    get netBalance() {
      return this.totalIncome - this.totalExpense;
    },
  };""",
    'Sekap Bungo-only finance summary'
)

# Reports: retain the original behaviour for every business except Sekap Bungo.
replace_once(
    'src/screens/ReportsScreen.tsx',
    """  const visibleSales = useMemo(() => {
    const sourceSales = isCashier ? sales : activeSales;
    return sourceSales.filter((sale) => {
      if (sale.businessId !== activeBusiness?.businessId) return false;
      if (!isCashier) return true;
      return sale.cashierUserId
        ? sale.cashierUserId === currentSession?.user.userId
        : sale.cashierName === currentSession?.user.fullName;
    });
  }, [activeSales, sales, activeBusiness?.businessId, currentSession?.user.userId, currentSession?.user.fullName, isCashier]);""",
    """  const isSekapBungo = activeBusiness?.businessId === 'biz-1790060286099';
  const activeOutletIds = useMemo(
    () => new Set(activeOutlets.filter((outlet) => outlet.status === 'ACTIVE').map((outlet) => outlet.outletId)),
    [activeOutlets]
  );

  const visibleSales = useMemo(() => {
    const sourceSales = isCashier ? sales : activeSales;
    return sourceSales.filter((sale) => {
      if (sale.businessId !== activeBusiness?.businessId) return false;
      if (isSekapBungo && (!sale.outletId || !activeOutletIds.has(sale.outletId))) return false;
      if (!isCashier) return true;
      return sale.cashierUserId
        ? sale.cashierUserId === currentSession?.user.userId
        : sale.cashierName === currentSession?.user.fullName;
    });
  }, [activeSales, sales, activeOutletIds, isSekapBungo, activeBusiness?.businessId, currentSession?.user.userId, currentSession?.user.fullName, isCashier]);""",
    'Sekap Bungo-only report sales filter'
)

replace_once(
    'src/screens/ReportsScreen.tsx',
    """    return periodLedgers.filter((entry) => {
      if (entry.businessId !== activeBusiness?.businessId || !entry.outletId) return false;
      if (isCashier && entry.outletId !== currentSession?.user.outletId) return false;""",
    """    return periodLedgers.filter((entry) => {
      if (entry.businessId !== activeBusiness?.businessId || !entry.outletId) return false;
      if (isSekapBungo && !activeOutletIds.has(entry.outletId)) return false;
      if (isCashier && entry.outletId !== currentSession?.user.outletId) return false;""",
    'Sekap Bungo-only ledger filter'
)
replace_once(
    'src/screens/ReportsScreen.tsx',
    """  }, [periodLedgers, activeBusiness?.businessId, isCashier, currentSession?.user.outletId, dateFilter]);""",
    """  }, [periodLedgers, activeBusiness?.businessId, activeOutletIds, isSekapBungo, isCashier, currentSession?.user.outletId, dateFilter]);""",
    'Sekap Bungo-only ledger dependencies'
)

replace_once(
    'src/screens/ReportsScreen.tsx',
    """    .map((outlet) => {
      const entries = filteredStanLedgers.filter((entry) => entry.outletId === outlet.outletId);
      const income = entries.filter((entry) => entry.type === 'PEMASUKAN').reduce((sum, entry) => sum + Number(entry.amount || 0), 0);
      const expense = entries.filter((entry) => entry.type === 'PENGELUARAN').reduce((sum, entry) => sum + Number(entry.amount || 0), 0);
      return { outletId: outlet.outletId, name: outlet.name, income, expense, net: income - expense };
    })
    .sort((a, b) => b.net - a.net), [activeOutlets, filteredStanLedgers, isCashier, currentSession?.user.outletId]);""",
    """    .map((outlet) => {
      const entries = filteredStanLedgers.filter((entry) => entry.outletId === outlet.outletId);
      const stanSales = filteredSales.filter((sale) => sale.outletId === outlet.outletId);
      const income = isSekapBungo
        ? stanSales.reduce((sum, sale) => sum + Number(sale.totalAmount || 0), 0)
        : entries.filter((entry) => entry.type === 'PEMASUKAN').reduce((sum, entry) => sum + Number(entry.amount || 0), 0);
      const expense = entries.filter((entry) => entry.type === 'PENGELUARAN').reduce((sum, entry) => sum + Number(entry.amount || 0), 0);
      return { outletId: outlet.outletId, name: outlet.name, income, expense, net: income - expense };
    })
    .sort((a, b) => b.net - a.net), [activeOutlets, filteredStanLedgers, filteredSales, isSekapBungo, isCashier, currentSession?.user.outletId]);""",
    'Sekap Bungo-only STAN income source'
)

replace_once(
    'src/screens/ReportsScreen.tsx',
    '<StatCard title="Total Penjualan" value={formatRupiah(totalSalesRevenue)} icon={<Receipt className="w-4 h-4" />} color="teal" subtitle={`${filteredSales.length} struk`} />',
    '<StatCard title={isSekapBungo ? "Total Pemasukan STAN Aktif" : "Total Penjualan"} value={formatRupiah(totalSalesRevenue)} icon={<Receipt className="w-4 h-4" />} color="teal" subtitle={isSekapBungo ? `${filteredSales.length} struk dari STAN aktif` : `${filteredSales.length} struk`} />',
    'Sekap Bungo-only report metric label'
)
replace_once(
    'src/screens/ReportsScreen.tsx',
    "['Total Penjualan', totalSalesRevenue],",
    "[isSekapBungo ? 'Total Pemasukan STAN Aktif' : 'Total Penjualan', totalSalesRevenue],",
    'Sekap Bungo-only export label'
)
replace_once(
    'src/screens/ReportsScreen.tsx',
    '<strong>Total penjualan:</strong> ${formatRupiah(totalSalesRevenue)}',
    '<strong>${isSekapBungo ? "Total pemasukan STAN aktif" : "Total penjualan"}:</strong> ${formatRupiah(totalSalesRevenue)}',
    'Sekap Bungo-only HTML report label'
)

# Finance screen wording follows the selected business; figures for other businesses remain ledger-based.
replace_once(
    'src/screens/FinanceScreen.tsx',
    'title="Total Pemasukan (Kredit)"',
    'title={activeBusiness?.businessId === "biz-1790060286099" ? "Total Pemasukan STAN Aktif" : "Total Pemasukan (Kredit)"}',
    'Sekap Bungo-only finance label'
)
replace_once(
    'src/screens/FinanceScreen.tsx',
    'subtitle="Penjualan kasir & pendapatan lain"',
    'subtitle={activeBusiness?.businessId === "biz-1790060286099" ? "Total penjualan POS dari seluruh STAN aktif" : "Penjualan kasir & pendapatan lain"}',
    'Sekap Bungo-only finance subtitle'
)

print('Applied active-STAN income reconciliation only to Sekap Bungo; other business reporting remains unchanged.')
