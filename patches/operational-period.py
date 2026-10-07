from pathlib import Path
ROOT = Path("project")

def replace(path, old, new, count=1):
    p = ROOT / path
    s = p.read_text()
    if old not in s:
        raise SystemExit("pattern missing in " + path)
    p.write_text(s.replace(old, new, count))

# Entity types
replace("src/types.ts",
"""export enum UserRole {""",
"""export interface OperationalPeriodEntity {
  periodId: string;
  businessId: string;
  periodKey: string;
  name: string;
  startDate: number;
  endDate: number;
  status: 'ACTIVE' | 'CLOSED';
  closedAt?: number;
  closedBy?: string;
  createdAt: number;
}

export enum UserRole {""")
replace("src/types.ts", "  | 'OWNER_DASHBOARD'\n", "  | 'OWNER_DASHBOARD'\n  | 'OPERATIONAL_PERIODS_MODULE'\n")
replace("src/types.ts", "  timestamp: number;\n}\n\nexport interface SaleOrderItem", "  timestamp: number;\n  periodId?: string;\n}\n\nexport interface SaleOrderItem")
replace("src/types.ts", "  timestamp: number;\n}\n\nexport interface CartItem", "  timestamp: number;\n  periodId?: string;\n}\n\nexport interface CartItem")

# Supabase schema
period_table = """-- 4. Table: operational_periods
CREATE TABLE IF NOT EXISTS public.operational_periods (
  period_id TEXT PRIMARY KEY,
  business_id TEXT NOT NULL,
  period_key TEXT NOT NULL,
  name TEXT NOT NULL,
  start_date BIGINT NOT NULL,
  end_date BIGINT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  closed_at BIGINT,
  closed_by TEXT,
  created_at BIGINT NOT NULL,
  UNIQUE (business_id, period_key)
);

"""
for path in ["src/lib/supabaseSchema.ts", "supabase-schema.sql"]:
    p=ROOT/path
    s=p.read_text()
    s=s.replace("-- 4. Table: sales (Transaksi Kasir POS Realtime)", period_table+"-- 4. Table: sales (Transaksi Kasir POS Realtime)", 1)
    s=s.replace("  timestamp BIGINT NOT NULL\n);\n\n-- Additive SERVICE POS migration", "  timestamp BIGINT NOT NULL,\n  period_id TEXT\n);\n\n-- Additive SERVICE POS migration", 1)
    s=s.replace("ALTER TABLE public.sales ADD COLUMN IF NOT EXISTS service_staff_id TEXT;", "ALTER TABLE public.sales ADD COLUMN IF NOT EXISTS period_id TEXT;\nALTER TABLE public.sales ADD COLUMN IF NOT EXISTS service_staff_id TEXT;", 1)
    s=s.replace("  created_by TEXT NOT NULL,\n  timestamp BIGINT NOT NULL\n);\n\n-- 6. Table: transfers", "  created_by TEXT NOT NULL,\n  timestamp BIGINT NOT NULL,\n  period_id TEXT\n);\nALTER TABLE public.ledgers ADD COLUMN IF NOT EXISTS period_id TEXT;\n\n-- 6. Table: transfers", 1)
    p.write_text(s)
p=ROOT/"supabase-migration-service-pos.sql"
p.write_text(p.read_text()+"""
\n-- Operational periods migration
CREATE TABLE IF NOT EXISTS public.operational_periods (
  period_id TEXT PRIMARY KEY,
  business_id TEXT NOT NULL,
  period_key TEXT NOT NULL,
  name TEXT NOT NULL,
  start_date BIGINT NOT NULL,
  end_date BIGINT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  closed_at BIGINT,
  closed_by TEXT,
  created_at BIGINT NOT NULL,
  UNIQUE (business_id, period_key)
);
ALTER TABLE public.sales ADD COLUMN IF NOT EXISTS period_id TEXT;
ALTER TABLE public.ledgers ADD COLUMN IF NOT EXISTS period_id TEXT;
""")

# Sync service
p=ROOT/"src/services/supabaseSyncService.ts"
s=p.read_text()
s=s.replace("  OutletStockEntity,\n", "  OutletStockEntity,\n  OperationalPeriodEntity,\n", 1)
s=s.replace("  onStockMutationsUpdated: (mutations: StockMutationEntity[]) => void;\n", "  onStockMutationsUpdated: (mutations: StockMutationEntity[]) => void;\n  onOperationalPeriodsUpdated: (periods: OperationalPeriodEntity[]) => void;\n", 1)
anchor="export type RealtimeStatus = 'CONNECTED' | 'CONNECTING' | 'LOCAL_OFFLINE' | 'ERROR';\n"
maps="""export function mapOperationalPeriodFromDb(row: any): OperationalPeriodEntity {
  return {
    periodId: row.period_id,
    businessId: row.business_id,
    periodKey: row.period_key,
    name: row.name,
    startDate: Number(row.start_date),
    endDate: Number(row.end_date),
    status: row.status === 'CLOSED' ? 'CLOSED' : 'ACTIVE',
    closedAt: row.closed_at ? Number(row.closed_at) : undefined,
    closedBy: row.closed_by || undefined,
    createdAt: Number(row.created_at),
  };
}

export function mapOperationalPeriodToDb(entity: OperationalPeriodEntity): any {
  return {
    period_id: entity.periodId,
    business_id: entity.businessId,
    period_key: entity.periodKey,
    name: entity.name,
    start_date: entity.startDate,
    end_date: entity.endDate,
    status: entity.status,
    closed_at: entity.closedAt || null,
    closed_by: entity.closedBy || null,
    created_at: entity.createdAt,
  };
}

"""
s=s.replace(anchor, anchor+maps, 1)
s=s.replace("    timestamp: Number(row.timestamp),\n  };\n}\n\nexport function mapSaleToDb", "    timestamp: Number(row.timestamp),\n    periodId: row.period_id || undefined,\n  };\n}\n\nexport function mapSaleToDb", 1)
s=s.replace("    timestamp: entity.timestamp,\n  };\n  if (entity.customerName)", "    timestamp: entity.timestamp,\n    period_id: (entity as any).periodId || null,\n  };\n  if (entity.customerName)", 1)
s=s.replace("    timestamp: Number(row.timestamp),\n  };\n}\n\nexport function mapTransferFromDb", "    timestamp: Number(row.timestamp),\n    periodId: row.period_id || undefined,\n  };\n}\n\nexport function mapTransferFromDb", 1)
s=s.replace("    timestamp: entity.timestamp,\n  };\n}\n\nexport function mapTransferFromDb", "    timestamp: entity.timestamp,\n    period_id: (entity as any).periodId || null,\n  };\n}\n\nexport function mapTransferFromDb", 1)
s=s.replace("      this.fetchTable('sales'),\n", "      this.fetchTable('sales'),\n      this.fetchTable('operational_periods'),\n", 1)
s=s.replace("        case 'sales':\n          if (data.length > 0) this.handlers.onSalesUpdated(data.map(mapSaleFromDb));\n          break;", "        case 'sales':\n          if (data.length > 0) this.handlers.onSalesUpdated(data.map(mapSaleFromDb));\n          break;\n        case 'operational_periods':\n          if (data.length > 0) this.handlers.onOperationalPeriodsUpdated(data.map(mapOperationalPeriodFromDb));\n          break;", 1)
s=s.replace("  public async syncSale(sale: SaleOrderEntity) {\n    await this.upsertRecord('sales', mapSaleToDb(sale));\n  }", "  public async syncSale(sale: SaleOrderEntity) {\n    await this.upsertRecord('sales', mapSaleToDb(sale));\n  }\n\n  public async syncOperationalPeriod(period: OperationalPeriodEntity) {\n    await this.upsertRecord('operational_periods', mapOperationalPeriodToDb(period));\n  }", 1)
p.write_text(s)

# Context
p=ROOT/"src/context/TgpContext.tsx"
s=p.read_text()
s=s.replace("  OutletStockEntity,\n", "  OutletStockEntity,\n  OperationalPeriodEntity,\n", 1)
s=s.replace("  activeSales: SaleOrderEntity[];\n", "  activeSales: SaleOrderEntity[];\n  operationalPeriods: OperationalPeriodEntity[];\n  activeOperationalPeriod: OperationalPeriodEntity | null;\n  periodSales: SaleOrderEntity[];\n  periodLedgers: LedgerTransactionEntity[];\n  createOperationalPeriod: (businessId: string) => boolean;\n  closeOperationalPeriod: (periodId: string) => boolean;\n", 1)
s=s.replace("  const [sales, setSales] = useState<SaleOrderEntity[]>(() => loadStored('sales', INITIAL_SALES));", "  const [sales, setSales] = useState<SaleOrderEntity[]>(() => loadStored('sales', INITIAL_SALES));\n  const [operationalPeriods, setOperationalPeriods] = useState<OperationalPeriodEntity[]>(() => loadStored('operational_periods', []));", 1)
marker="      onStatusChanged: (status, message) => {"
handler="""      onOperationalPeriodsUpdated: (remote) => {
        setOperationalPeriods((prev) => {
          const map = new Map<string, OperationalPeriodEntity>(prev.map((p) => [p.periodId, p]));
          remote.forEach((p) => map.set(p.periodId, p));
          return Array.from(map.values()).sort((a, b) => b.startDate - a.startDate);
        });
      },
"""
s=s.replace(marker, handler+marker, 1)
s=s.replace("  useEffect(() => saveStored('sales', sales), [sales]);", "  useEffect(() => saveStored('sales', sales), [sales]);\n  useEffect(() => saveStored('operational_periods', operationalPeriods), [operationalPeriods]);", 1)
old="""  const activeSales = activeBusinessId
    ? sales.filter((s) => s.businessId === activeBusinessId)
    : [];
"""
new="""  const periodKeyFor = (timestamp: number): string => {
    const d = new Date(timestamp);
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
  };

  const ensureActivePeriod = (businessId: string): OperationalPeriodEntity => {
    const now = new Date();
    const key = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
    const existing = operationalPeriods.find((p) => p.businessId === businessId && p.periodKey === key);
    if (existing) return existing;
    const start = new Date(now.getFullYear(), now.getMonth(), 1);
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    const period: OperationalPeriodEntity = {
      periodId: 'period-' + businessId + '-' + key,
      businessId,
      periodKey: key,
      name: start.toLocaleDateString('id-ID', { month: 'long', year: 'numeric' }),
      startDate: start.getTime(),
      endDate: end.getTime() - 1,
      status: 'ACTIVE',
      createdAt: Date.now(),
    };
    setOperationalPeriods((prev) => [period, ...prev]);
    supabaseSyncService.syncOperationalPeriod(period);
    return period;
  };

  const activeOperationalPeriod = activeBusinessId ? ensureActivePeriod(activeBusinessId) : null;
  const periodSales = activeOperationalPeriod
    ? sales.filter((s) => s.businessId === activeOperationalPeriod.businessId && periodKeyFor(s.timestamp) === activeOperationalPeriod.periodKey)
    : [];
  const periodLedgers = activeOperationalPeriod
    ? ledgers.filter((l) => l.businessId === activeOperationalPeriod.businessId && periodKeyFor(l.timestamp) === activeOperationalPeriod.periodKey)
    : [];
  const activeSales = activeBusinessId ? periodSales : [];
"""
if old not in s: raise SystemExit("activeSales marker missing")
s=s.replace(old,new,1)
marker="  const clearMessages = () => {"
actions="""  const createOperationalPeriod = (businessId: string): boolean => {
    const role = currentSession ? normalizeUserRole(currentSession.user.role) : null;
    if (role !== UserRole.OWNER && role !== UserRole.ADMIN_OWNER) {
      setErrorMessage('Hanya OWNER atau ADMIN OWNER yang dapat mengelola periode operasional.');
      return false;
    }
    const biz = businesses.find((b) => b.businessId === businessId);
    if (!biz) return false;
    const allowed = role === UserRole.OWNER
      ? biz.ownerId === currentSession?.user.userId
      : (currentSession?.user.assignedBusinessIds || []).includes(businessId);
    if (!allowed) {
      setErrorMessage('Anda tidak memiliki akses ke bisnis ini.');
      return false;
    }
    const period = ensureActivePeriod(businessId);
    setUserMessage('Periode ' + period.name + ' siap digunakan.');
    return true;
  };

  const closeOperationalPeriod = (periodId: string): boolean => {
    const role = currentSession ? normalizeUserRole(currentSession.user.role) : null;
    if (role !== UserRole.OWNER && role !== UserRole.ADMIN_OWNER) {
      setErrorMessage('Hanya OWNER atau ADMIN OWNER yang dapat menutup periode.');
      return false;
    }
    const period = operationalPeriods.find((p) => p.periodId === periodId);
    if (!period) return false;
    const biz = businesses.find((b) => b.businessId === period.businessId);
    const allowed = role === UserRole.OWNER
      ? biz?.ownerId === currentSession?.user.userId
      : (currentSession?.user.assignedBusinessIds || []).includes(period.businessId);
    if (!allowed) {
      setErrorMessage('Anda tidak berwenang menutup periode bisnis ini.');
      return false;
    }
    if (period.status === 'CLOSED') return true;
    const closed: OperationalPeriodEntity = { ...period, status: 'CLOSED', closedAt: Date.now(), closedBy: currentSession?.user.username };
    setOperationalPeriods((prev) => prev.map((p) => p.periodId === periodId ? closed : p));
    supabaseSyncService.syncOperationalPeriod(closed);
    addAuditLog('OPERATIONAL_PERIOD_CLOSED', 'Periode ' + period.name + ' ditutup. Data tetap tersimpan.', period.businessId);
    setUserMessage('Periode ' + period.name + ' ditutup. Data tidak dihapus.');
    return true;
  };

"""
s=s.replace(marker, actions+marker,1)
marker2="    const activeBiz = businesses.find((b) => b.businessId === effectiveBusinessId);"
guard="""    const checkoutPeriod = ensureActivePeriod(effectiveBusinessId);
    if (checkoutPeriod.status === 'CLOSED') {
      setErrorMessage('Periode ' + checkoutPeriod.name + ' sudah ditutup. Transaksi baru tidak dapat dibuat pada periode tertutup.');
      return null;
    }

"""
s=s.replace(marker2,guard+marker2,1)
s=s.replace("      timestamp: nowTs,\n    };\n    setSales((prev) => [newSale, ...prev]);", "      timestamp: nowTs,\n      periodId: checkoutPeriod.periodId,\n    };\n    setSales((prev) => [newSale, ...prev]);",1)
s=s.replace("      createdBy: currentSession.user.username,\n    };\n    setLedgers((prev) => [newLedger, ...prev]);", "      createdBy: currentSession.user.username,\n      periodId: checkoutPeriod.periodId,\n    };\n    setLedgers((prev) => [newLedger, ...prev]);",1)
nav="    if (screen === 'REPORTS_MODULE' && role !== UserRole.OWNER && role !== UserRole.ADMIN_OWNER && role !== UserRole.KASIR) {"
s=s.replace(nav, "    if (screen === 'OPERATIONAL_PERIODS_MODULE' && role !== UserRole.OWNER && role !== UserRole.ADMIN_OWNER) {\n      setErrorMessage('Akses ditolak: Periode Operasional hanya untuk OWNER atau ADMIN OWNER.');\n      return;\n    }\n"+nav,1)
s=s.replace("        activeSales,\n", "        activeSales,\n        operationalPeriods,\n        activeOperationalPeriod,\n        periodSales,\n        periodLedgers,\n        createOperationalPeriod,\n        closeOperationalPeriod,\n",1)
p.write_text(s)

# App screen
replace("src/App.tsx", "import { PosScreen } from './screens/PosScreen';", "import { PosScreen } from './screens/PosScreen';\nimport { OperationalPeriodsScreen } from './screens/OperationalPeriodsScreen';")
replace("src/App.tsx", "      case 'POS_MODULE':", "      case 'OPERATIONAL_PERIODS_MODULE':\n        return <OperationalPeriodsScreen />;\n      case 'POS_MODULE':")

# Screen
(ROOT/"src/screens/OperationalPeriodsScreen.tsx").write_text("""import React from 'react';
import { CalendarDays, LockKeyhole, ShieldCheck } from 'lucide-react';
import { useTgp } from '../context/TgpContext';
import { UserRole } from '../types';

const money = (n: number) => 'Rp ' + Math.round(n).toLocaleString('id-ID');

export const OperationalPeriodsScreen: React.FC = () => {
  const { currentSession, authorizedBusinesses, activeBusiness, setActiveBusiness, activeOperationalPeriod, operationalPeriods, periodSales, periodLedgers, createOperationalPeriod, closeOperationalPeriod } = useTgp();
  const role = currentSession?.user.role;
  if (role !== UserRole.OWNER && role !== UserRole.ADMIN_OWNER) return <div className="p-6 bg-white rounded-3xl">Akses ditolak.</div>;

  const businesses = authorizedBusinesses.filter((b) => role === UserRole.OWNER ? b.ownerId === currentSession?.user.userId : (currentSession?.user.assignedBusinessIds || []).includes(b.businessId));
  const periods = operationalPeriods.filter((p) => activeBusiness && p.businessId === activeBusiness.businessId).sort((a,b) => b.startDate-a.startDate);
  const salesTotal = periodSales.reduce((a,s) => a + Number(s.totalAmount || 0), 0);
  const incomeTotal = periodLedgers.filter((l) => l.type === 'PEMASUKAN').reduce((a,l) => a + Number(l.amount || 0), 0);

  return <div className="space-y-5 pb-20">
    <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div><div className="flex items-center gap-2 text-blue-700 text-xs font-extrabold uppercase"><CalendarDays className="w-4 h-4"/> Periode Operasional</div>
        <h2 className="text-xl font-black mt-1">Jual-Beli per Bulan</h2>
        <p className="text-xs text-slate-500 mt-1">Data transaksi lama tetap tersimpan. Periode yang ditutup menjadi arsip read-only.</p></div>
        <ShieldCheck className="w-7 h-7 text-emerald-600"/>
      </div>
    </div>

    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {businesses.map((b) => <button key={b.businessId} onClick={() => { setActiveBusiness(b.businessId); createOperationalPeriod(b.businessId); }} className={"text-left p-4 rounded-2xl border " + (activeBusiness?.businessId === b.businessId ? "border-blue-400 bg-blue-50" : "border-slate-200 bg-white")}>
        <div className="font-extrabold">{b.name}</div><div className="text-xs text-slate-500 mt-1">Kelola periode bisnis</div>
      </button>)}
    </div>

    {activeBusiness && <><div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div className="bg-white rounded-2xl border p-4"><div className="text-xs text-slate-500">Periode</div><div className="font-black mt-1">{activeOperationalPeriod?.name || '-'}</div></div>
      <div className="bg-white rounded-2xl border p-4"><div className="text-xs text-slate-500">Status</div><div className="font-black mt-1">{activeOperationalPeriod?.status || '-'}</div></div>
      <div className="bg-white rounded-2xl border p-4"><div className="text-xs text-slate-500">Penjualan</div><div className="font-black mt-1">{money(salesTotal)}</div></div>
      <div className="bg-white rounded-2xl border p-4"><div className="text-xs text-slate-500">Pemasukan</div><div className="font-black mt-1">{money(incomeTotal)}</div></div>
    </div>
    {activeOperationalPeriod?.status === 'ACTIVE' && <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
      <div><div className="font-extrabold text-amber-900">Tutup {activeOperationalPeriod.name}?</div><p className="text-xs text-amber-800 mt-1">Transaksi tidak dihapus. Kasir akan menggunakan periode aktif berikutnya.</p></div>
      <button onClick={() => closeOperationalPeriod(activeOperationalPeriod.periodId)} className="px-4 py-2 rounded-xl bg-amber-600 text-white text-xs font-extrabold flex items-center gap-2"><LockKeyhole className="w-4 h-4"/> Tutup Periode</button>
    </div>}
    <div className="bg-white rounded-3xl border overflow-hidden"><div className="p-4 border-b font-black">Riwayat Periode</div>
      {periods.map((p) => <div key={p.periodId} className="p-4 border-b last:border-0 flex items-center justify-between gap-3"><div><div className="font-bold">{p.name}</div><div className="text-xs text-slate-500">{p.periodKey} · {p.status === 'CLOSED' ? 'Ditutup' : 'Aktif'}</div></div><span className={"px-2.5 py-1 rounded-full text-[10px] font-black " + (p.status === 'CLOSED' ? "bg-slate-100 text-slate-600" : "bg-emerald-100 text-emerald-700")}>{p.status}</span></div>)}
      {periods.length === 0 && <div className="p-8 text-center text-sm text-slate-500">Belum ada arsip periode.</div>}
    </div></>}
  </div>;
};
""")

# Bottom navigation
p=ROOT/"src/components/TgpBottomBar.tsx"
s=p.read_text()
s=s.replace("  Building2,\n", "  Building2,\n  Calendar,\n",1)
s=s.replace("  } else if (role === UserRole.OWNER) {\n    navItems = [", "  } else if (role === UserRole.OWNER) {\n    navItems = [",1)
# Owner gets period tab.
needle="""      {
        screen: 'BUSINESS_HOME',
        label: 'Operasional',
        icon: <Store className="w-5 h-5" />,
      },"""
replacement="""      {
        screen: 'BUSINESS_HOME',
        label: 'Operasional',
        icon: <Store className="w-5 h-5" />,
      },
      {
        screen: 'OPERATIONAL_PERIODS_MODULE',
        label: 'Periode',
        icon: <Calendar className="w-5 h-5" />,
      },"""
if needle not in s: raise SystemExit("owner nav marker missing")
s=s.replace(needle,replacement,1)
# Admin owner gets period tab.
needle2="""    if (role === UserRole.ADMIN_OWNER) {
      if (activeBusiness?.activeModules.includes(BusinessModule.FINANCE)) {"""
replacement2="""    if (role === UserRole.ADMIN_OWNER) {
      navItems.push({
        screen: 'OPERATIONAL_PERIODS_MODULE',
        label: 'Periode',
        icon: <Calendar className="w-5 h-5" />,
      });
      if (activeBusiness?.activeModules.includes(BusinessModule.FINANCE)) {"""
if needle2 not in s: raise SystemExit("admin nav marker missing")
s=s.replace(needle2,replacement2,1)
p.write_text(s)

print("Operational period patch complete")
