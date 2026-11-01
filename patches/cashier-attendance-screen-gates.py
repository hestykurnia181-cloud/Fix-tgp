from pathlib import Path
import re

root = Path("project/src/screens")

def replace_once(path_name: str, old: str, new: str, label: str):
    path = root / path_name
    source = path.read_text(encoding="utf-8")
    if new in source:
        print(f"[attendance-gates] already applied: {label}")
        return source
    if old not in source:
        raise RuntimeError(f"[attendance-gates] anchor missing in {path_name}: {label}")
    source = source.replace(old, new, 1)
    path.write_text(source, encoding="utf-8")
    print(f"[attendance-gates] applied: {label}")
    return source

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

closing = root / "CashierClosingScreen.tsx"
source = closing.read_text(encoding="utf-8")
if "const latestTodayAttendance=activeAttendances" not in source:
    pattern = re.compile(
        r"(?m)^(?P<i>[ \t]*)const today=new Date\(\)\.toDateString\(\);[ \t]*\r?\n"
        r"[ \t]*const clockedIn=activeAttendances\.some\([^\r\n]*\);[ \t]*\r?\n"
        r"[ \t]*const clockedOut=activeAttendances\.some\([^\r\n]*\);"
    )
    replacement = (
        "  const today=new Date().toDateString();\n"
        "  const latestTodayAttendance=activeAttendances\n"
        "    .filter(a=>a.userId===currentSession?.user.userId&&a.businessId===activeBusiness?.businessId&&new Date(a.timestamp).toDateString()===today)\n"
        "    .sort((a,b)=>b.timestamp-a.timestamp)[0];\n"
        "  const clockedIn=latestTodayAttendance?.type==='MASUK';\n"
        "  const clockedOut=latestTodayAttendance?.type==='PULANG'||!latestTodayAttendance;"
    )
    source, count = pattern.subn(replacement, source, count=1)
    if count != 1:
        raise RuntimeError("[attendance-gates] could not locate closing attendance state declarations")
    closing.write_text(source, encoding="utf-8")
    print("[attendance-gates] applied: closing latest attendance state")
else:
    print("[attendance-gates] already applied: closing latest attendance state")

old_disabled = "mine.some(c=>c.shiftStartedAt===Math.max(0,...activeAttendances.filter(a=>a.userId===currentSession?.user.userId&&a.type==='MASUK').map(a=>a.timestamp)))"
new_disabled = "mine.some(c=>c.shiftStartedAt===(latestTodayAttendance?.type==='MASUK'?latestTodayAttendance.timestamp:0))"
source = closing.read_text(encoding="utf-8")
if new_disabled not in source:
    if old_disabled not in source:
        raise RuntimeError("[attendance-gates] closing duplicate-shift check anchor missing")
    closing.write_text(source.replace(old_disabled, new_disabled, 1), encoding="utf-8")
    print("[attendance-gates] applied: closing duplicate-shift check for current session")

print("[attendance-gates] cashier stock input and closing now use latest same-day attendance.")
