from pathlib import Path
import re

ROOT = Path("project")

def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(label + " anchor not found")
    return text.replace(old, new, 1)

ctx = ROOT / "src/context/TgpContext.tsx"
if not ctx.exists():
    raise RuntimeError("TgpContext.tsx not found")
s = ctx.read_text()

if "logout: () => void;" not in s:
    m = re.search(r"(\n\s*currentSession:\s*[^;]+;)", s)
    if not m:
        raise RuntimeError("currentSession contract anchor not found")
    s = s[:m.end()] + "\n  logout: () => void;" + s[m.end():]

if "const logout = () => {" not in s:
    s = replace_once(s, "  const clearMessages = () => {", """  const logout = () => {
    try {
      Object.keys(localStorage)
        .filter((key) => /session|auth/i.test(key) && !/pending_sync/i.test(key))
        .forEach((key) => localStorage.removeItem(key));
    } catch {}
    setCurrentSession(null);
  };

  const clearMessages = () => {""", "logout implementation")

if "  sales: SaleOrderEntity[];" not in s and "  activeSales: SaleOrderEntity[];" in s:
    s = replace_once(s, "  activeSales: SaleOrderEntity[];", "  sales: SaleOrderEntity[];\n  activeSales: SaleOrderEntity[];", "sales context type")
if re.search(r"\n\s*sales,\n", s) is None and "        activeSales," in s:
    s = replace_once(s, "        activeSales,", "        sales,\n        activeSales,", "sales provider value")
if re.search(r"\n\s*logout,\n", s) is None and "        activeSales," in s:
    s = replace_once(s, "        activeSales,", "        logout,\n        activeSales,", "logout provider value")
ctx.write_text(s)

types = ROOT / "src/types.ts"
if types.exists():
    t = types.read_text()
    if "'SERVICE_STAFF_MODULE'" not in t and "'OPERATIONAL_PERIODS_MODULE'\n" in t:
        t = t.replace("  | 'OPERATIONAL_PERIODS_MODULE'\n", "  | 'OPERATIONAL_PERIODS_MODULE'\n  | 'SERVICE_STAFF_MODULE'\n", 1)
        types.write_text(t)

app = ROOT / "src/App.tsx"
if app.exists():
    t = app.read_text()
    if "ServiceStaffScreen" not in t:
        t = replace_once(t, "import { PosScreen } from './screens/PosScreen';", "import { PosScreen } from './screens/PosScreen';\nimport { ServiceStaffScreen } from './screens/ServiceStaffScreen';", "ServiceStaffScreen import")
    if "case 'SERVICE_STAFF_MODULE':" not in t:
        t = replace_once(t, "      case 'POS_MODULE':", "      case 'SERVICE_STAFF_MODULE':\n        return <ServiceStaffScreen />;\n      case 'POS_MODULE':", "ServiceStaffScreen route")
    app.write_text(t)

staff = ROOT / "src/screens/ServiceStaffScreen.tsx"
if staff.exists():
    t = staff.read_text()
    t = re.sub(r"const \{currentSession,activeBusiness,operationalPeriods\}=useTgp\(\);", "const {currentSession,activeBusiness,operationalPeriods,sales,logout}=useTgp();", t, count=1)
    t = re.sub(r"\s*let sales:any\[\]=\[\];try\{sales=JSON\.parse\(localStorage\.getItem\('sales'\)\|\|'\[\]'\)\}catch\{sales=\[\]\}", "", t, count=1)
    t = re.sub(r"\s*let all:any\[\]=\[\];try\{all=JSON\.parse\(localStorage\.getItem\('sales'\)\|\|'\[\]'\)\}catch\{\}", "", t, count=1)
    t = t.replace("return all.flatMap((sale:any)=>", "return sales.flatMap((sale:any)=>")
    t = re.sub(r"(\},\[)(user\?\.userId,user\?\.username,user\?\.fullName,)", r"\1sales,\2", t, count=1)
    t = re.sub(r"(\},\[)(user\?\.userId,)", r"\1sales,\2", t, count=1)

    old_block = """         matches(item.serviceStaffId)||matches(item.staffId)||matches(item.assignedStaffId)||
         matches(item.serviceStaff?.userId)||matches(item.serviceStaff?.username)||
         matches(item.staff?.userId)||matches(item.staff?.username)||
         matches(sale.serviceStaffId)||matches(sale.staffId)||matches(sale.assignedStaffId);"""
    new_block = """         matches(item.serviceStaffId)||matches(item.staffId)||matches(item.assignedStaffId)||
         matches(item.serviceStaffName)||matches(item.assignedStaffName)||
         matches(item.serviceStaff?.userId)||matches(item.serviceStaff?.username)||matches(item.serviceStaff?.fullName)||
         matches(item.staff?.userId)||matches(item.staff?.username)||matches(item.staff?.fullName)||
         matches(sale.serviceStaffId)||matches(sale.staffId)||matches(sale.assignedStaffId)||
         matches(sale.serviceStaffName)||matches(sale.assignedStaffName);"""
    if old_block in t:
        t = t.replace(old_block, new_block, 1)

    if "onClick={logout}" not in t and 'Jasa Saya' in t:
        t = t.replace('<h2 className="text-xl font-black">Jasa Saya</h2>', '<h2 className="text-xl font-black">Jasa Saya</h2><button type="button" onClick={logout} className="ml-auto px-3 py-2 rounded-xl bg-slate-900 text-white text-xs font-extrabold">Keluar</button>', 1)
    staff.write_text(t)

sync = ROOT / "src/services/supabaseSyncService.ts"
if not sync.exists():
    raise RuntimeError("supabaseSyncService.ts not found")
q = sync.read_text()

old_raw = """      const { error } = await supabase.from(table).upsert(dbPayload);
      if (error) {
        console.warn("[SupabaseSync] Error upserting to " + table + ":", error.message);
      }
      if (this.channel) {"""
if old_raw in q:
    q = q.replace(old_raw, """      const { error } = await supabase.from(table).upsert(dbPayload);
      if (error) {
        console.warn("[SupabaseSync] Error upserting to " + table + ":", error.message);
        throw error;
      }
      if (this.channel) {""", 1)

if "startPendingSyncRetry" not in q and "public async flushPendingSync()" in q:
    q = q.replace("  public async flushPendingSync() {", """  public startPendingSyncRetry() {
    if (typeof window === 'undefined') return;
    const retry = () => { void this.flushPendingSync(); };
    window.addEventListener('online', retry);
    if (navigator.onLine) retry();
  }

  public async flushPendingSync() {""", 1)

if "this.startPendingSyncRetry();" not in q and "    this.startRealtimeSync();" in q:
    q = q.replace("    this.startRealtimeSync();", "    this.startRealtimeSync();\n    this.startPendingSyncRetry();", 1)

sync.write_text(q)
print("Staff history + reliable Supabase synchronization patch prepared")
