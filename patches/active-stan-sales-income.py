from pathlib import Path

ROOT = Path('project')

def replace_once(path, old, new, label):
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if new in s:
        return
    if old not in s:
        raise SystemExit(f'Missing required anchor ({label}) in {path}')
    p.write_text(s.replace(old, new, 1), encoding='utf-8')

# Finance summary: use POS sales from currently active STANs, not ledger credits.
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
    """  const activeStanOutletIds = new Set(activeOutlets.map((outlet) => outlet.outletId));
  const activeStanSales = periodSales.filter(
    (sale) => !!sale.outletId && activeStanOutletIds.has(sale.outletId)
  );
  const activeBusinessFinance = {
    totalIncome: activeStanSales.reduce((sum, sale) => sum + Number(sale.totalAmount || 0), 0),
    totalExpense: periodLedgers
      .filter((l) => l.type === LedgerType.PENGELUARAN)
      .reduce((sum, l) => sum + l.amount, 0),
    get netBalance() {
      return this.totalIncome - this.totalExpense;
    },
  };""",
    'active business finance total'
)

# All report entry points use the same active-STAN sales scope.
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
    """  const activeOutletIds = useMemo(
    () => new Set(activeOutlets.filter((outlet) => outlet.status === 'ACTIVE').map((outlet) => outlet.outletId)),
    [activeOutlets]
  );

  const visibleSales = useMemo(() => {
    const sourceSales = isCashier ? sales : activeSales;
    return sourceSales.filter((sale) => {
      if (sale.businessId !== activeBusiness?.businessId) return false;
      if (!sale.outletId || !activeOutletIds.has(sale.outletId)) return false;
      if (!isCashier) return true;
      return sale.cashierUserId
        ? sale.cashierUserId === currentSession?.user.userId
        : sale.cashierName === currentSession?.user.fullName;
    });
  }, [activeSales, sales, activeOutletIds, activeBusiness?.businessId, currentSession?.user.userId, currentSession?.user.fullName, isCashier]);""",
    'active STAN sales filtering'
)

replace_once(
    'src/screens/ReportsScreen.tsx',
    """    return periodLedgers.filter((entry) => {
      if (entry.businessId !== activeBusiness?.businessId || !entry.outletId) return false;
      if (isCashier && entry.outletId !== currentSession?.user.outletId) return false;""",
    """    return periodLedgers.filter((entry) => {
      if (entry.businessId !== activeBusiness?.businessId || !entry.outletId) return false;
      if (!activeOutletIds.has(entry.outletId)) return false;
      if (isCashier && entry.outletId !== currentSession?.user.outletId) return false;""",
    'active STAN ledger filter'
)
replace_once(
    'src/screens/ReportsScreen.tsx',
    """  }, [periodLedgers, activeBusiness?.businessId, isCashier, currentSession?.user.outletId, dateFilter]);""",
    """  }, [periodLedgers, activeBusiness?.businessId, activeOutletIds, isCashier, currentSession?.user.outletId, dateFilter]);""",
    'active STAN ledger dependencies'
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
      const income = stanSales.reduce((sum, sale) => sum + Number(sale.totalAmount || 0), 0);
      const expense = entries.filter((entry) => entry.type === 'PENGELUARAN').reduce((sum, entry) => sum + Number(entry.amount || 0), 0);
      return { outletId: outlet.outletId, name: outlet.name, income, expense, net: income - expense };
    })
    .sort((a, b) => b.net - a.net), [activeOutlets, filteredStanLedgers, filteredSales, isCashier, currentSession?.user.outletId]);""",
    'per STAN report income source'
)

replace_once(
    'src/screens/ReportsScreen.tsx',
    '<StatCard title="Total Penjualan" value={formatRupiah(totalSalesRevenue)} icon={<Receipt className="w-4 h-4" />} color="teal" subtitle={`${filteredSales.length} struk`} />',
    '<StatCard title="Total Pemasukan STAN Aktif" value={formatRupiah(totalSalesRevenue)} icon={<Receipt className="w-4 h-4" />} color="teal" subtitle={`${filteredSales.length} struk dari STAN aktif`} />',
    'report metric label'
)
replace_once('src/screens/ReportsScreen.tsx', "['Total Penjualan', totalSalesRevenue],", "['Total Pemasukan STAN Aktif', totalSalesRevenue], 'excel summary label')
replace_once(
    'src/screens/ReportsScreen.tsx',
    '<strong>Total penjualan:</strong> ${formatRupiah(totalSalesRevenue)}',
    '<strong>Total pemasukan STAN aktif:</strong> ${formatRupiah(totalSalesRevenue)}',
    'html report summary label'
)

replace_once('src/screens/FinanceScreen.tsx', 'title="Total Pemasukan (Kredit)"', 'title="Total Pemasukan STAN Aktif"', 'finance metric label')
replace_once(
    'src/screens/FinanceScreen.tsx',
    'subtitle="Penjualan kasir & pendapatan lain"',
    'subtitle="Total penjualan POS dari seluruh STAN aktif"',
    'finance metric subtitle'
)

print('Active-STAN sales income alignment applied to finance summary and sales reports.')
