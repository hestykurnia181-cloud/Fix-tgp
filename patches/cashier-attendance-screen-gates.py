from pathlib import Path

root = Path("project/src/screens")

def replace_once(path_name: str, old: str, new: str, label: str):
    path = root / path_name
    source = path.read_text(encoding="utf-8")
    if new in source:
        print(f"[attendance-gates] already applied: {label}")
        return
    if old not in source:
        raise RuntimeError(f"[attendance-gates] anchor missing in {path_name}: {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")
    print(f"[attendance-gates] applied: {label}")

replace_once(
    "CashierStockInScreen.tsx",
    """  const today = new Date().toDateString();
  const hasIn = activeAttendances.some((a)=>a.userId===currentSession?.user.userId && a.type==='MASUK' && new Date(a.timestamp).toDateString()===today);
  const hasOut = activeAttendances.some((a)=>a.userId===currentSession?.user.userId && a.type==='PULANG' && new Date(a.timestamp).toDateString()===today);""",
    """  const today = new Date().toDateString();
  const latestTodayAttendance = activeAttendances
    .filter((a) => a.userId === currentSession?.user.userId && a.businessId === activeBusiness?.businessId && new Date(a.timestamp).toDateString() === today)
    .sort((a, b) => b.timestamp - a.timestamp)[0];
  const clockedIn = latestTodayAttendance?.type === 'MASUK';""",
    "stock input latest attendance state"
)
replace_once(
    "CashierStockInScreen.tsx",
    "  if(!hasIn || hasOut) return <div className=\"rounded-3xl bg-white border p-8 text-center\"><Store className=\"mx-auto w-10 h-10 text-amber-500\"/><h2 className=\"font-extrabold mt-3\">Input stok terkunci</h2><p className=\"text-xs text-slate-500 mt-1\">Kasir harus absen masuk dan belum absen pulang untuk menginput stok.</p></div>;",
    "  if(!clockedIn) return <div className=\"rounded-3xl bg-white border p-8 text-center\"><Store className=\"mx-auto w-10 h-10 text-amber-500\"/><h2 className=\"font-extrabold mt-3\">Input stok terkunci</h2><p className=\"text-xs text-slate-500 mt-1\">Kasir harus memiliki absensi terakhir MASUK untuk menginput stok.</p></div>;",
    "stock input latest-state gate"
)

replace_once(
    "CashierClosingScreen.tsx",
    """  const today=new Date().toDateString();
  const clockedIn=activeAttendances.some(a=>a.userId===currentSession?.user.userId&&a.type==='MASUK'&&new Date(a.timestamp).toDateString()===today);
  const clockedOut=activeAttendances.some(a=>a.userId===currentSession?.user.userId&&a.type==='PULANG'&&new Date(a.timestamp).toDateString()===today);""",
    """  const today=new Date().toDateString();
  const latestTodayAttendance=activeAttendances
    .filter(a=>a.userId===currentSession?.user.userId&&a.businessId===activeBusiness?.businessId&&new Date(a.timestamp).toDateString()===today)
    .sort((a,b)=>b.timestamp-a.timestamp)[0];
  const clockedIn=latestTodayAttendance?.type==='MASUK';
  const clockedOut=latestTodayAttendance?.type==='PULANG'||!latestTodayAttendance;""",
    "closing latest attendance state"
)
replace_once(
    "CashierClosingScreen.tsx",
    "mine.some(c=>c.shiftStartedAt===Math.max(0,...activeAttendances.filter(a=>a.userId===currentSession?.user.userId&&a.type==='MASUK').map(a=>a.timestamp)))",
    "mine.some(c=>c.shiftStartedAt===(latestTodayAttendance?.type==='MASUK'?latestTodayAttendance.timestamp:0))",
    "closing duplicate-shift check scoped to current active session"
)

print("[attendance-gates] cashier stock input and closing now share latest same-day attendance semantics.")
