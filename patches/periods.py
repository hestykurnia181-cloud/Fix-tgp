from pathlib import Path
ROOT=Path("project")

def must_replace(path, old, new, count=1):
    p=ROOT/path
    s=p.read_text()
    if old not in s:
        raise RuntimeError("missing pattern: "+path+" :: "+old[:80])
    p.write_text(s.replace(old,new,count))

# types
must_replace("src/types.ts",
"export enum UserRole {",
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
must_replace("src/types.ts","  | 'OWNER_DASHBOARD'\n","  | 'OWNER_DASHBOARD'\n  | 'OPERATIONAL_PERIODS_MODULE'\n")
must_replace("src/types.ts","  timestamp: number;\n  createdAt?: number;\n}","  timestamp: number;\n  createdAt?: number;\n  periodId?: string;\n}",1)
must_replace("src/types.ts","  date?: number;\n  createdBy: string;\n}","  date?: number;\n  createdBy: string;\n  periodId?: string;\n}",1)

# schema
period="""-- 4. Table: operational_periods
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
for name in ["src/lib/supabaseSchema.ts","supabase-schema.sql"]:
    p=ROOT/name
    s=p.read_text()
    s=s.replace("-- 4. Table: sales (Transaksi Kasir POS Realtime)",period+"-- 4. Table: sales (Transaksi Kasir POS Realtime)",1)
    s=s.replace("  timestamp BIGINT NOT NULL\n);\n\n-- Additive SERVICE POS migration","  timestamp BIGINT NOT NULL,\n  period_id TEXT\n);\n\n-- Additive SERVICE POS migration",1)
    s=s.replace("ALTER TABLE public.sales ADD COLUMN IF NOT EXISTS service_staff_id TEXT;","ALTER TABLE public.sales ADD COLUMN IF NOT EXISTS period_id TEXT;\nALTER TABLE public.sales ADD COLUMN IF NOT EXISTS service_staff_id TEXT;",1)
    s=s.replace("  created_by TEXT NOT NULL,\n  timestamp BIGINT NOT NULL\n);\n\n-- 6. Table: transfers","  created_by TEXT NOT NULL,\n  timestamp BIGINT NOT NULL,\n  period_id TEXT\n);\nALTER TABLE public.ledgers ADD COLUMN IF NOT EXISTS period_id TEXT;\n\n-- 6. Table: transfers",1)
    p.write_text(s)
p=ROOT/"supabase-migration-service-pos.sql"
p.write_text(p.read_text()+"\n"+period+"ALTER TABLE public.sales ADD COLUMN IF NOT EXISTS period_id TEXT;\nALTER TABLE public.ledgers ADD COLUMN IF NOT EXISTS period_id TEXT;\n")

# sync service
p=ROOT/"src/services/supabaseSyncService.ts"
s=p.read_text()
s=s.replace("  OutletStockEntity,\n","  OutletStockEntity,\n  OperationalPeriodEntity,\n",1)
s=s.replace("  onStockMutationsUpdated: (mutations: StockMutationEntity[]) => void;\n","  onStockMutationsUpdated: (mutations: StockMutationEntity[]) => void;\n  onOperationalPeriodsUpdated: (periods: OperationalPeriodEntity[]) => void;\n",1)
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
s=s.replace(anchor,anchor+maps,1)
# sale mapper
s=s.replace("    timestamp: Number(row.timestamp),\n  };\n}\n\nexport function mapSaleToDb","    timestamp: Number(row.timestamp),\n    periodId: row.period_id || undefined,\n  };\n}\n\nexport function mapSaleToDb",1)
s=s.replace("    timestamp: entity.timestamp,\n  };\n  if (entity.customerName)","    timestamp: entity.timestamp,\n    period_id: (entity as any).periodId || null,\n  };\n  if (entity.customerName)",1)
# ledger mapper
s=s.replace("    timestamp: Number(row.timestamp),\n  };\n}\n\nexport function mapLedgerToDb","    timestamp: Number(row.timestamp),\n    periodId: row.period_id || undefined,\n  };\n}\n\nexport function mapLedgerToDb",1)
s=s.replace("    timestamp: entity.timestamp,\n  };\n}\n\nexport function mapTransferFromDb","    timestamp: entity.timestamp,\n    period_id: (entity as any).periodId || null,\n  };\n}\n\nexport function mapTransferFromDb",1)
s=s.replace("      this.fetchTable('sales'),\n","      this.fetchTable('sales'),\n      this.fetchTable('operational_periods'),\n",1)
s=s.replace("        case 'sales':\n          if (data.length > 0) this.handlers.onSalesUpdated(data.map(mapSaleFromDb));\n          break;","        case 'sales':\n          if (data.length > 0) this.handlers.onSalesUpdated(data.map(mapSaleFromDb));\n          break;\n        case 'operational_periods':\n          if (data.length > 0) this.handlers.onOperationalPeriodsUpdated(data.map(mapOperationalPeriodFromDb));\n          break;",1)
s=s.replace("  public async syncSale(sale: SaleOrderEntity) {\n    await this.upsertRecord('sales', mapSaleToDb(sale));\n  }","  public async syncSale(sale: SaleOrderEntity) {\n    await this.upsertRecord('sales', mapSaleToDb(sale));\n  }\n  public async syncOperationalPeriod(period: OperationalPeriodEntity) {\n    await this.upsertRecord('operational_periods', mapOperationalPeriodToDb(period));\n  }",1)
p.write_text(s)

# context
p=ROOT/"src/context/TgpContext.tsx"
s=p.read_text()
s=s.replace("  OutletStockEntity,\n","  OutletStockEntity,\n  OperationalPeriodEntity,\n",1)
s=s.replace("  activeSales: SaleOrderEntity[];\n","  activeSales: SaleOrderEntity[];\n  operationalPeriods: OperationalPeriodEntity[];\n  activeOperationalPeriod: OperationalPeriodEntity | null;\n  periodSales: SaleOrderEntity[];\n  periodLedgers: LedgerTransactionEntity[];\n  createOperationalPeriod: (businessId: string) => boolean;\n  closeOperationalPeriod: (periodId: string) => boolean;\n",1)
s=s.replace("  const [sales, setSales] = useState<SaleOrderEntity[]>(() => loadStored('sales', INITIAL_SALES));","  const [sales, setSales] = useState<SaleOrderEntity[]>(() => loadStored('sales', INITIAL_SALES));\n  const [operationalPeriods, setOperationalPeriods] = useState<OperationalPeriodEntity[]>(() => loadStored('operational_periods', []));",1)
s=s.replace("      onStatusChanged: (status, message) => {","      onOperationalPeriodsUpdated: (remote) => {\n        setOperationalPeriods((prev) => {\n          const map = new Map<string, OperationalPeriodEntity>(prev.map((p) => [p.periodId, p]));\n          remote.forEach((p) => map.set(p.periodId, p));\n          return Array.from(map.values()).sort((a,b) => b.startDate-a.startDate);\n        });\n      },\n      onStatusChanged: (status, message) => {",1)
s=s.replace("  useEffect(() => saveStored('sales', sales), [sales]);","  useEffect(() => saveStored('sales', sales), [sales]);\n  useEffect(() => saveStored('operational_periods', operationalPeriods), [operationalPeriods]);",1)
old="""  const activeSales = activeBusinessId
    ? sales.filter((s) => s.businessId === activeBusinessId)
    : [];
"""
new="""  const currentPeriodKey = (): string => {
    const d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0');
  };
  const periodKeyForTimestamp = (timestamp:number): string => {
    const d = new Date(timestamp);
    return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0');
  };
  const ensureActivePeriod = (businessId: string): OperationalPeriodEntity => {
    const key=currentPeriodKey();
    const found=operationalPeriods.find(p=>p.businessId===businessId && p.periodKey===key);
    if(found) return found;
    const d=new Date();
    const start=new Date(d.getFullYear(),d.getMonth(),1);
    const end=new Date(d.getFullYear(),d.getMonth()+1,1);
    const p: OperationalPeriodEntity={periodId:'period-'+businessId+'-'+key,businessId,periodKey:key,name:start.toLocaleDateString('id-ID',{month:'long',year:'numeric'}),startDate:start.getTime(),endDate:end.getTime()-1,status:'ACTIVE',createdAt:Date.now()};
    setOperationalPeriods(prev=>[p,...prev]);
    supabaseSyncService.syncOperationalPeriod(p);
    return p;
  };
  useEffect(() => {
    if (!activeBusinessId) return;
    const key = currentPeriodKey();
    if (!operationalPeriods.some(p => p.businessId === activeBusinessId && p.periodKey === key)) {
      ensureActivePeriod(activeBusinessId);
    }
  }, [activeBusinessId, operationalPeriods.length]);

  const currentKey=currentPeriodKey();
  const activeOperationalPeriod=activeBusinessId ? (operationalPeriods.find(p=>p.businessId===activeBusinessId && p.periodKey===currentKey) || null) : null;
  const periodSales=activeOperationalPeriod ? sales.filter(s=>s.businessId===activeOperationalPeriod.businessId && (((s as any).periodId===activeOperationalPeriod.periodId) || (!(s as any).periodId && periodKeyForTimestamp(s.timestamp)===activeOperationalPeriod.periodKey))) : [];
  const periodLedgers=activeOperationalPeriod ? ledgers.filter(l=>l.businessId===activeOperationalPeriod.businessId && (((l as any).periodId===activeOperationalPeriod.periodId) || (!(l as any).periodId && periodKeyForTimestamp(l.timestamp)===activeOperationalPeriod.periodKey))) : [];
  const activeSales=activeBusinessId ? periodSales : [];
"""
if old not in s: raise SystemExit("activeSales pattern missing")
s=s.replace(old,new,1)
marker="  const clearMessages = () => {"
actions="""  const createOperationalPeriod=(businessId:string):boolean=>{
    const role=currentSession ? normalizeUserRole(currentSession.user.role) : null;
    if(role!==UserRole.OWNER && role!==UserRole.ADMIN_OWNER){setErrorMessage('Hanya OWNER atau ADMIN OWNER yang dapat mengelola periode operasional.');return false;}
    const biz=businesses.find(b=>b.businessId===businessId);
    const allowed=role===UserRole.OWNER ? biz?.ownerId===currentSession?.user.userId : (currentSession?.user.assignedBusinessIds||[]).includes(businessId);
    if(!biz || !allowed){setErrorMessage('Anda tidak memiliki akses ke bisnis ini.');return false;}
    const p=ensureActivePeriod(businessId); setUserMessage('Periode '+p.name+' siap digunakan.'); return true;
  };
  const closeOperationalPeriod=(periodId:string):boolean=>{
    const role=currentSession ? normalizeUserRole(currentSession.user.role) : null;
    if(role!==UserRole.OWNER && role!==UserRole.ADMIN_OWNER){setErrorMessage('Hanya OWNER atau ADMIN OWNER yang dapat menutup periode.');return false;}
    const p=operationalPeriods.find(x=>x.periodId===periodId); if(!p)return false;
    const biz=businesses.find(b=>b.businessId===p.businessId);
    const allowed=role===UserRole.OWNER ? biz?.ownerId===currentSession?.user.userId : (currentSession?.user.assignedBusinessIds||[]).includes(p.businessId);
    if(!allowed){setErrorMessage('Anda tidak berwenang menutup periode ini.');return false;}
    const closed={...p,status:'CLOSED' as const,closedAt:Date.now(),closedBy:currentSession?.user.username};
    setOperationalPeriods(prev=>prev.map(x=>x.periodId===periodId?closed:x)); supabaseSyncService.syncOperationalPeriod(closed);
    addAuditLog('OPERATIONAL_PERIOD_CLOSED','Periode '+p.name+' ditutup. Data transaksi tetap tersimpan.',p.businessId);
    setUserMessage('Periode '+p.name+' ditutup. Data tidak dihapus.'); return true;
  };

"""
s=s.replace(marker,actions+marker,1)
marker2="    const activeBiz = businesses.find((b) => b.businessId === effectiveBusinessId);"
s=s.replace(marker2,"    const checkoutPeriod=ensureActivePeriod(effectiveBusinessId);\n    if(checkoutPeriod.status==='CLOSED'){setErrorMessage('Periode '+checkoutPeriod.name+' sudah ditutup. Transaksi baru tidak dapat dibuat.');return null;}\n\n"+marker2,1)
s=s.replace("      timestamp: nowTs,\n    };\n    setSales((prev) => [newSale, ...prev]);","      timestamp: nowTs,\n      periodId: checkoutPeriod.periodId,\n    };\n    setSales((prev) => [newSale, ...prev]);",1)
s=s.replace("      createdBy: currentSession.user.username,\n    };\n    setLedgers((prev) => [newLedger, ...prev]);","      createdBy: currentSession.user.username,\n      periodId: checkoutPeriod.periodId,\n    };\n    setLedgers((prev) => [newLedger, ...prev]);",1)
s=s.replace("    if (screen === 'REPORTS_MODULE' && role !== UserRole.OWNER && role !== UserRole.ADMIN_OWNER && role !== UserRole.KASIR) {","    if (screen === 'OPERATIONAL_PERIODS_MODULE' && role !== UserRole.OWNER && role !== UserRole.ADMIN_OWNER) {\n      setErrorMessage('Akses ditolak: Periode Operasional hanya untuk OWNER atau ADMIN OWNER.'); return;\n    }\n    if (screen === 'REPORTS_MODULE' && role !== UserRole.OWNER && role !== UserRole.ADMIN_OWNER && role !== UserRole.KASIR) {",1)
s=s.replace("        activeSales,\n","        activeSales,\n        operationalPeriods,\n        activeOperationalPeriod,\n        periodSales,\n        periodLedgers,\n        createOperationalPeriod,\n        closeOperationalPeriod,\n",1)
p.write_text(s)

# App
must_replace("src/App.tsx","import { PosScreen } from './screens/PosScreen';","import { PosScreen } from './screens/PosScreen';\nimport { OperationalPeriodsScreen } from './screens/OperationalPeriodsScreen';")
must_replace("src/App.tsx","      case 'POS_MODULE':","      case 'OPERATIONAL_PERIODS_MODULE':\n        return <OperationalPeriodsScreen />;\n      case 'POS_MODULE':")


# Finance must use the active operational period, not the whole business ledger.
must_replace("src/context/TgpContext.tsx",
"""  const activeBusinessFinance = {
    totalIncome: activeLedger
      .filter((l) => l.type === LedgerType.PEMASUKAN)
      .reduce((sum, l) => sum + l.amount, 0),
    totalExpense: activeLedger
      .filter((l) => l.type === LedgerType.PENGELUARAN)
      .reduce((sum, l) => sum + l.amount, 0),
""",
"""  const activeBusinessFinance = {
    totalIncome: periodLedgers
      .filter((l) => l.type === LedgerType.PEMASUKAN)
      .reduce((sum, l) => sum + l.amount, 0),
    totalExpense: periodLedgers
      .filter((l) => l.type === LedgerType.PENGELUARAN)
      .reduce((sum, l) => sum + l.amount, 0),
""",1)

# Manual finance entries must belong to the current period and must be blocked after close.
must_replace("src/context/TgpContext.tsx",
"""    const nowTs = Date.now();
    const entry: LedgerTransactionEntity = {
      transactionId: 'ledger-manual-' + nowTs,""",
"""    const nowTs = Date.now();
    const manualPeriod = activeOperationalPeriod || ensureActivePeriod(activeBusinessId);
    if (manualPeriod.status === 'CLOSED') {
      setErrorMessage('Periode ' + manualPeriod.name + ' sudah ditutup. Transaksi kas baru tidak dapat dibuat.');
      return false;
    }
    const entry: LedgerTransactionEntity = {
      transactionId: 'ledger-manual-' + nowTs,""",1)

must_replace("src/context/TgpContext.tsx",
"""      createdBy: currentSession?.user.username || 'staff',
    };

    setLedgers((prev) => [entry, ...prev]);""",
"""      createdBy: currentSession?.user.username || 'staff',
      periodId: manualPeriod.periodId,
    };

    setLedgers((prev) => [entry, ...prev]);""",1)

# Finance screen: all rows and counters must be scoped to the active operational period.
must_replace("src/screens/FinanceScreen.tsx",
"""    activeBusiness,
    activeLedgers,
    activeBusinessFinance,""",
"""    activeBusiness,
    periodLedgers,
    activeBusinessFinance,""",1)

must_replace("src/screens/FinanceScreen.tsx","""  const filteredLedgers = activeLedgers.filter((l) => {""","""  const filteredLedgers = periodLedgers.filter((l) => {""",1)
must_replace("src/screens/FinanceScreen.tsx","""              Semua ({activeLedgers.length})""","""              Semua ({periodLedgers.length})""",1)



# Service POS: completing a barbershop/service sale must not require a tenant,
# outlet/stan selection, or a barber/staff assignment. Business context is taken
# from the already-active business; staff assignment remains optional metadata.
must_replace("src/screens/PosScreen.tsx",
"""  const hasStanModule = activeBusiness?.activeModules.includes(BusinessModule.STAN_OUTLET);
  const isServiceBusiness = activeBusiness?.templateType === BusinessTemplate.SERVICE;""",
"""  const isServiceBusiness = activeBusiness?.templateType === BusinessTemplate.SERVICE;
  const hasStanModule = activeBusiness?.activeModules.includes(BusinessModule.STAN_OUTLET);
  const shouldUseStan = hasStanModule && !isServiceBusiness;""",1)

must_replace("src/screens/PosScreen.tsx",
"""addToCart(quantityModalItem, validQty, hasStanModule ? selectedOutletId : undefined);""",
"""        addToCart(quantityModalItem, validQty, shouldUseStan ? selectedOutletId : undefined);""",1)

must_replace("src/screens/PosScreen.tsx",
"""    const sale = checkout(
      pm,
      hasStanModule && selectedOutletId ? selectedOutletId : undefined,""",
"""    const sale = checkout(
      pm,
      shouldUseStan && selectedOutletId ? selectedOutletId : undefined,""",1)

must_replace("src/screens/PosScreen.tsx",
"""        {hasStanModule && activeOutlets.length > 0 && (""",
"""        {shouldUseStan && activeOutlets.length > 0 && (""",1)

must_replace("src/screens/PosScreen.tsx",
"""                    (isServiceBusiness && cart.some((c) => c.item.type === 'SERVICE' && !c.serviceStaffId))
""",
"""                    false
""",1)

must_replace("src/screens/PosScreen.tsx",
"""                              <p className="text-[10px] text-slate-500">Pilih staff yang mengerjakan jasa ini.</p>""",
"""                              <p className="text-[10px] text-slate-500">Petugas jasa opsional; transaksi tetap bisa diselesaikan tanpa memilih staff.</p>""",1)

must_replace("src/screens/PosScreen.tsx",
"""                              <span className="text-[10px] font-black px-2 py-1 rounded-lg bg-white border border-blue-100 text-blue-700">Per item jasa</span>""",
"""                              <span className="text-[10px] font-black px-2 py-1 rounded-lg bg-white border border-blue-100 text-blue-700">Opsional</span>""",1)

must_replace("src/screens/PosScreen.tsx",
"""                                <option value="">Pilih staff...</option>""",
"""                                <option value="">Tanpa petugas</option>""",1)

must_replace("src/screens/PosScreen.tsx",
"""                              {cartEntry.serviceStaffId ? `Snapshot pembagian: ${cartEntry.serviceCommissionPercent ?? assignedServiceStaff?.serviceCommissionPercent ?? 0}% untuk ${cartEntry.serviceStaffName || assignedServiceStaff?.fullName || 'staff'}.` : 'Staff wajib dipilih sebelum pembayaran.'}""",
"""                              {cartEntry.serviceStaffId ? `Snapshot pembagian: ${cartEntry.serviceCommissionPercent ?? assignedServiceStaff?.serviceCommissionPercent ?? 0}% untuk ${cartEntry.serviceStaffName || assignedServiceStaff?.fullName || 'staff'}.` : 'Petugas belum ditentukan. Seluruh nilai jasa masuk sebagai pendapatan bisnis.'}""",1)

must_replace("src/context/TgpContext.tsx",
"""      if (serviceCartEntries.some((ci) => !ci.serviceStaffId)) {
        setErrorMessage('Setiap jasa di keranjang wajib memilih staff/petugas yang mengerjakannya.');
        return null;
      }

      const totalServiceCommission = detailedItems.reduce((sum, item) => sum + (item.serviceCommissionAmount || 0), 0);""",
"""      // Petugas jasa bersifat opsional. Jika tidak dipilih, tidak ada komisi
      // yang dipotong dan seluruh nilai jasa menjadi bagian bisnis.
      const totalServiceCommission = detailedItems.reduce((sum, item) => sum + (item.serviceCommissionAmount || 0), 0);""",1)

# Never force an outlet for a service business. A barbershop/service POS is
# completed against the already-active business context.
must_replace("src/context/TgpContext.tsx",
"""    if (role === UserRole.KASIR && !targetOutletId) {
      setErrorMessage('Akun Kasir belum memiliki STAN/Outlet penugasan. Silakan minta Admin Owner menugaskan STAN/Outlet terlebih dahulu.');
      return null;
    }""",
"""    if (role === UserRole.KASIR && !targetOutletId && businesses.find((b) => b.businessId === effectiveBusinessId)?.templateType !== BusinessTemplate.SERVICE) {
      setErrorMessage('Akun Kasir belum memiliki STAN/Outlet penugasan. Silakan minta Admin Owner menugaskan STAN/Outlet terlebih dahulu.');
      return null;
    }""",1)

must_replace("src/context/TgpContext.tsx",
"""    if (role === UserRole.KASIR && !targetOutlet) {
      setErrorMessage('STAN/Outlet Kasir tidak ditemukan atau sudah dihapus. Hubungi Admin.');
      return null;
    }""",
"""    if (role === UserRole.KASIR && !targetOutlet && businesses.find((b) => b.businessId === effectiveBusinessId)?.templateType !== BusinessTemplate.SERVICE) {
      setErrorMessage('STAN/Outlet Kasir tidak ditemukan atau sudah dihapus. Hubungi Admin.');
      return null;
    }""",1)



# SERVICE STAFF MODULE
p=ROOT/"src/types.ts"
t=p.read_text()
if "'SERVICE_STAFF_MODULE'" not in t:
    t=t.replace("  | 'OPERATIONAL_PERIODS_MODULE'\n","  | 'OPERATIONAL_PERIODS_MODULE'\n  | 'SERVICE_STAFF_MODULE'\n",1)
    p.write_text(t)

(ROOT/"src/screens/ServiceStaffScreen.tsx").write_text(r"""import React,{useMemo,useRef,useState} from 'react';
import {Camera,CheckCircle2,Clock3,Scissors,UserRound,CalendarDays} from 'lucide-react';
import {useTgp} from '../context/TgpContext';
import {UserRole} from '../types';

type Attendance={id:string;userId:string;businessId:string;dateKey:string;checkInAt?:number;checkInPhoto?:string;checkOutAt?:number;checkOutPhoto?:string};
const KEY='tgp_service_attendance_v1';
const readRows=():Attendance[]=>{try{return JSON.parse(localStorage.getItem(KEY)||'[]')}catch{return[]}};
const saveRows=(x:Attendance[])=>localStorage.setItem(KEY,JSON.stringify(x));
const keyOf=(d:Date)=>{const x=new Date(d.getTime()-d.getTimezoneOffset()*60000);return x.toISOString().slice(0,10)};
const weekStart=(d:Date)=>{const x=new Date(d);const n=x.getDay()||7;x.setHours(0,0,0,0);x.setDate(x.getDate()-n+1);return x.getTime()};
const money=(n:number)=>'Rp '+Math.round(n).toLocaleString('id-ID');

export const ServiceStaffScreen:React.FC=()=>{
 const {currentSession,activeBusiness,operationalPeriods}=useTgp();
 const user=currentSession?.user, role=currentSession?.user.role;
 const [rows,setRows]=useState<Attendance[]>(readRows); const [target,setTarget]=useState<'IN'|'OUT'|null>(null);
 const [periodId,setPeriodId]=useState('CURRENT'); const [range,setRange]=useState<'DAY'|'WEEK'|'MONTH'|'ALL'>('DAY');
 const ref=useRef<HTMLInputElement>(null);
 const allowed=role===UserRole.STAFF||role===UserRole.ADMIN_OWNER;
 const today=keyOf(new Date());
 const todayRow=rows.find(x=>x.userId===user?.userId&&x.businessId===activeBusiness?.businessId&&x.dateKey===today);
 const periods=useMemo(()=>operationalPeriods.filter(p=>p.businessId===activeBusiness?.businessId).sort((a,b)=>b.startDate-a.startDate),[operationalPeriods,activeBusiness?.businessId]);
 const period=periodId==='CURRENT'?(periods.find(p=>p.status==='ACTIVE')||periods[0]):periods.find(p=>p.periodId===periodId);
 const history=useMemo(()=>{
   if(!user||!activeBusiness)return[];
   let all:any[]=[];try{all=JSON.parse(localStorage.getItem('sales')||'[]')}catch{}
   const now=new Date(),ws=weekStart(now),ms=new Date(now.getFullYear(),now.getMonth(),1).getTime();
   return all.flatMap((sale:any)=>{
     if(sale.businessId!==activeBusiness.businessId)return[];
     const ts=Number(sale.timestamp||sale.createdAt||0), sd=new Date(ts);
     if(period&&(sale.periodId? sale.periodId!==period.periodId : (sd.getFullYear()+'-'+String(sd.getMonth()+1).padStart(2,'0'))!==period.periodKey))return[];
     if(range==='DAY'&&keyOf(sd)!==today)return[];
     if(range==='WEEK'&&ts<ws)return[];
     if(range==='MONTH'&&ts<ms)return[];
     return (Array.isArray(sale.items)?sale.items:[]).filter((i:any)=>i.serviceStaffId===user.userId||i.serviceStaffId===user.username||i.serviceStaffName===user.fullName).map((i:any)=>({id:(sale.saleId||sale.orderId||sale.transactionId)+'-'+(i.itemId||i.name),ts,name:i.name||i.itemName||i.serviceName||'Jasa',amount:Number(i.subtotal??i.total??i.amount??((i.price||0)*(i.quantity||1))),qty:Number(i.quantity||1),commission:Number(i.serviceCommissionAmount||0)}));
   }).sort((a:any,b:any)=>b.ts-a.ts);
 },[user?.userId,user?.username,user?.fullName,activeBusiness?.businessId,period?.periodId,period?.periodKey,range,today]);
 const total=history.reduce((a:number,x:any)=>a+x.amount,0),commission=history.reduce((a:number,x:any)=>a+x.commission,0);
 const choose=(x:'IN'|'OUT')=>{setTarget(x);ref.current?.click()};
 const photo=(e:React.ChangeEvent<HTMLInputElement>)=>{
   const f=e.target.files?.[0];if(!f||!target||!user||!activeBusiness)return;
   const r=new FileReader();r.onload=()=>{const rows=readRows(),dk=keyOf(new Date()),old=rows.find(x=>x.userId===user.userId&&x.businessId===activeBusiness.businessId&&x.dateKey===dk),a:Attendance=old||{id:'att-'+user.userId+'-'+dk,userId:user.userId,businessId:activeBusiness.businessId,dateKey:dk};if(target==='IN'){a.checkInAt=Date.now();a.checkInPhoto=String(r.result||'')}else{a.checkOutAt=Date.now();a.checkOutPhoto=String(r.result||'')};const n=[...rows.filter(x=>x.id!==a.id),a];saveRows(n);setRows(n);setTarget(null);e.target.value=''};r.readAsDataURL(f)
 };
 if(!allowed)return <div className="p-6">Akses ditolak.</div>;
 return <div className="space-y-4 pb-24">
  <input ref={ref} type="file" accept="image/*" capture="user" onChange={photo} className="hidden"/>
  <div className="bg-white rounded-3xl border p-5"><div className="flex items-center gap-3"><div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center"><Scissors className="w-6 h-6"/></div><div><div className="text-[10px] uppercase font-black text-emerald-700">Jasa • {activeBusiness?.name||'Sky barbershop'}</div><h2 className="text-xl font-black">Jasa & Absensi</h2><p className="text-xs text-slate-500">Hanya absensi dan riwayat jasa akun ini.</p></div></div></div>
  <div className="bg-white rounded-3xl border p-4"><div className="flex items-center gap-2 mb-3"><Camera className="w-4 h-4 text-emerald-600"/><b>Absensi Hari Ini</b></div><div className="grid sm:grid-cols-2 gap-3"><button onClick={()=>choose('IN')} disabled={!!todayRow?.checkInAt} className="rounded-2xl p-4 border text-left disabled:opacity-50 bg-emerald-50 border-emerald-200"><b>Absen Masuk</b><div className="text-xs mt-1">{todayRow?.checkInAt?new Date(todayRow.checkInAt).toLocaleTimeString('id-ID'):'Ambil foto untuk masuk'}</div></button><button onClick={()=>choose('OUT')} disabled={!todayRow?.checkInAt||!!todayRow?.checkOutAt} className="rounded-2xl p-4 border text-left disabled:opacity-50 bg-blue-50 border-blue-200"><b>Absen Pulang</b><div className="text-xs mt-1">{todayRow?.checkOutAt?new Date(todayRow.checkOutAt).toLocaleTimeString('id-ID'):'Ambil foto untuk pulang'}</div></button></div>{todayRow?.checkInPhoto&&<div className="mt-3 flex gap-2"><img src={todayRow.checkInPhoto} className="w-16 h-16 rounded-xl object-cover border"/>{todayRow.checkOutPhoto&&<img src={todayRow.checkOutPhoto} className="w-16 h-16 rounded-xl object-cover border"/>}</div>}</div>
  <div className="bg-white rounded-3xl border p-4"><div className="flex items-center gap-2 mb-3"><CalendarDays className="w-4 h-4 text-blue-600"/><b>Riwayat Jasa Saya</b></div><div className="grid sm:grid-cols-2 gap-2 mb-3"><select value={periodId} onChange={e=>setPeriodId(e.target.value)} className="rounded-xl border px-3 py-2 text-sm"><option value="CURRENT">Periode aktif</option>{periods.map(p=><option key={p.periodId} value={p.periodId}>{p.name} • {p.status}</option>)}</select><div className="grid grid-cols-4 gap-1 bg-slate-100 rounded-xl p-1">{([['DAY','Harian'],['WEEK','Mingguan'],['MONTH','Bulanan'],['ALL','Semua']] as const).map(([k,l])=><button key={k} onClick={()=>setRange(k)} className={'rounded-lg py-2 text-[10px] font-black '+(range===k?'bg-white shadow':'text-slate-500')}>{l}</button>)}</div></div><div className="grid grid-cols-2 gap-2 mb-3"><div className="rounded-2xl bg-slate-50 p-3"><div className="text-[10px] text-slate-500">Total Jasa</div><b>{money(total)}</b></div><div className="rounded-2xl bg-slate-50 p-3"><div className="text-[10px] text-slate-500">Komisi</div><b>{money(commission)}</b></div></div><div className="divide-y border rounded-2xl overflow-hidden">{history.length?history.map((x:any)=><div key={x.id} className="p-3 flex justify-between"><div><b className="text-sm">{x.name}</b><div className="text-[10px] text-slate-500">{new Date(x.ts).toLocaleString('id-ID')} • Qty {x.qty}</div></div><b>{money(x.amount)}</b></div>):<div className="p-6 text-center text-sm text-slate-400"><UserRound className="w-6 h-6 mx-auto mb-2"/>Belum ada riwayat jasa pada filter ini.</div>}</div></div>
 </div>
};
""")

p=ROOT/"src/screens/ServiceStaffScreen.tsx"
p.parent.mkdir(parents=True,exist_ok=True)
if not p.exists():
    pass

p=ROOT/"src/App.tsx";t=p.read_text()
if "ServiceStaffScreen" not in t:
    t=t.replace("import { PosScreen } from './screens/PosScreen';","import { PosScreen } from './screens/PosScreen';\nimport { ServiceStaffScreen } from './screens/ServiceStaffScreen';",1)
    t=t.replace("      case 'POS_MODULE':","      case 'SERVICE_STAFF_MODULE':\n        return <ServiceStaffScreen />;\n      case 'POS_MODULE':",1)
p.write_text(t)

p=ROOT/"src/components/TgpBottomBar.tsx";t=p.read_text()
if "SERVICE_STAFF_MODULE" not in t:
    a="    if (role === UserRole.ADMIN_OWNER) {"
    if a in t:t=t.replace(a,a+"\n      navItems.push({ screen: 'SERVICE_STAFF_MODULE', label: 'Jasa', icon: <span className=\"text-lg leading-none\">✂️</span> });",1)
    t=t.replace("    return navItems;","    if (role === UserRole.STAFF) navItems.push({ screen: 'SERVICE_STAFF_MODULE', label: 'Jasa', icon: <span className=\"text-lg leading-none\">✂️</span> });\n\n    return navItems;",1)
p.write_text(t)

# UI
(ROOT/"src/screens/OperationalPeriodsScreen.tsx").write_text("""import React from 'react';
import { CalendarDays, LockKeyhole, ShieldCheck } from 'lucide-react';
import { useTgp } from '../context/TgpContext';
import { UserRole } from '../types';

const money=(n:number)=>'Rp '+Math.round(n).toLocaleString('id-ID');

export const OperationalPeriodsScreen:React.FC=()=>{
 const {currentSession,authorizedBusinesses,activeBusiness,setActiveBusiness,activeOperationalPeriod,operationalPeriods,periodSales,periodLedgers,createOperationalPeriod,closeOperationalPeriod}=useTgp();
 const role=currentSession?.user.role;
 if(role!==UserRole.OWNER&&role!==UserRole.ADMIN_OWNER)return <div className="p-6 bg-white rounded-3xl">Akses ditolak.</div>;
 const businesses=authorizedBusinesses.filter(b=>role===UserRole.OWNER?b.ownerId===currentSession?.user.userId:(currentSession?.user.assignedBusinessIds||[]).includes(b.businessId));
 const periods=operationalPeriods.filter(p=>activeBusiness&&p.businessId===activeBusiness.businessId).sort((a,b)=>b.startDate-a.startDate);
 const sales=periodSales.reduce((a,s)=>a+Number(s.totalAmount||0),0);
 const income=periodLedgers.filter(l=>l.type==='PEMASUKAN').reduce((a,l)=>a+Number(l.amount||0),0);
 return <div className="space-y-5 pb-20">
  <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm flex justify-between"><div><div className="flex gap-2 text-blue-700 text-xs font-extrabold uppercase"><CalendarDays className="w-4 h-4"/>Periode Operasional</div><h2 className="text-xl font-black mt-1">Jual-Beli per Bulan</h2><p className="text-xs text-slate-500 mt-1">Data lama tetap tersimpan; periode tutup menjadi read-only.</p></div><ShieldCheck className="w-7 h-7 text-emerald-600"/></div>
  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">{businesses.map(b=><button key={b.businessId} onClick={()=>{setActiveBusiness(b.businessId);createOperationalPeriod(b.businessId)}} className={"text-left p-4 rounded-2xl border "+(activeBusiness?.businessId===b.businessId?'border-blue-400 bg-blue-50':'border-slate-200 bg-white')}><div className="font-extrabold">{b.name}</div><div className="text-xs text-slate-500 mt-1">Kelola periode</div></button>)}</div>
  {activeBusiness&&<><div className="grid grid-cols-2 lg:grid-cols-4 gap-3"><div className="bg-white rounded-2xl border p-4"><div className="text-xs text-slate-500">Periode</div><div className="font-black mt-1">{activeOperationalPeriod?.name||'-'}</div></div><div className="bg-white rounded-2xl border p-4"><div className="text-xs text-slate-500">Status</div><div className="font-black mt-1">{activeOperationalPeriod?.status||'-'}</div></div><div className="bg-white rounded-2xl border p-4"><div className="text-xs text-slate-500">Penjualan</div><div className="font-black mt-1">{money(sales)}</div></div><div className="bg-white rounded-2xl border p-4"><div className="text-xs text-slate-500">Pemasukan</div><div className="font-black mt-1">{money(income)}</div></div></div>
  {activeOperationalPeriod?.status==='ACTIVE'&&<div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex justify-between items-center gap-3"><div><div className="font-extrabold text-amber-900">Tutup {activeOperationalPeriod.name}?</div><div className="text-xs text-amber-800">Transaksi tidak dihapus.</div></div><button onClick={()=>closeOperationalPeriod(activeOperationalPeriod.periodId)} className="px-4 py-2 rounded-xl bg-amber-600 text-white text-xs font-extrabold flex gap-2"><LockKeyhole className="w-4 h-4"/>Tutup Periode</button></div>}
  <div className="bg-white rounded-3xl border overflow-hidden"><div className="p-4 border-b font-black">Riwayat Periode</div>{periods.map(p=><div key={p.periodId} className="p-4 border-b last:border-0 flex justify-between"><div><div className="font-bold">{p.name}</div><div className="text-xs text-slate-500">{p.periodKey}</div></div><span className="text-[10px] font-black">{p.status}</span></div>)}</div></>}
 </div>;
};
""")

p=ROOT/"src/components/TgpBottomBar.tsx"
s=p.read_text().replace("  Building2,\n","  Building2,\n  Calendar,\n",1)
needle="""      {
        screen: 'BUSINESS_HOME',
        label: 'Operasional',
        icon: <Store className="w-5 h-5" />,
      },"""
s=s.replace(needle,needle+"""
      {
        screen: 'OPERATIONAL_PERIODS_MODULE',
        label: 'Periode',
        icon: <Calendar className="w-5 h-5" />,
      },""",1)
needle2="""    if (role === UserRole.ADMIN_OWNER) {
      if (activeBusiness?.activeModules.includes(BusinessModule.FINANCE)) {"""
s=s.replace(needle2,"""    if (role === UserRole.ADMIN_OWNER) {
      navItems.push({
        screen: 'OPERATIONAL_PERIODS_MODULE',
        label: 'Periode',
        icon: <Calendar className="w-5 h-5" />,
      });
      if (activeBusiness?.activeModules.includes(BusinessModule.FINANCE)) {""",1)
p.write_text(s)

print("period patch OK")
