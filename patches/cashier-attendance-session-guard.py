from pathlib import Path

p = Path("project/src/context/TgpContext.tsx")
s = p.read_text(encoding="utf-8")

old_nav = """      if (screen === 'CASHIER_STOCK_IN_MODULE') { const today = new Date().toDateString(); const hasIn = attendances.some(a=>a.userId===currentSession.user.userId&&a.type==='MASUK'&&new Date(a.timestamp).toDateString()===today); const hasOut = attendances.some(a=>a.userId===currentSession.user.userId&&a.type==='PULANG'&&new Date(a.timestamp).toDateString()===today); if (!hasIn || hasOut) { setErrorMessage('Menu input stok hanya dapat dibuka setelah absen masuk dan sebelum absen pulang.'); return; } }"""
new_nav = """      if (screen === 'CASHIER_STOCK_IN_MODULE') {
        const today = new Date().toDateString();
        const latestTodayAttendance = attendances
          .filter((a) => a.userId === currentSession.user.userId && a.businessId === activeBusinessId && new Date(a.timestamp).toDateString() === today)
          .sort((a, b) => b.timestamp - a.timestamp)[0];
        if (latestTodayAttendance?.type !== 'MASUK') {
          setErrorMessage('Menu input stok hanya dapat dibuka setelah absen masuk dan sebelum absen pulang.');
          return;
        }
      }"""
if new_nav not in s:
    if old_nav not in s:
        raise SystemExit("Cashier attendance session guard: navigation guard anchor missing")
    s = s.replace(old_nav, new_nav, 1)

old_transfer = """      const today = new Date().toDateString();
      const clockedIn = attendances.some((a) => a.userId === currentSession?.user.userId && a.businessId === activeBusinessId && a.type === 'MASUK' && new Date(a.timestamp).toDateString() === today);
      const clockedOut = attendances.some((a) => a.userId === currentSession?.user.userId && a.businessId === activeBusinessId && a.type === 'PULANG' && new Date(a.timestamp).toDateString() === today);"""
new_transfer = """      const today = new Date().toDateString();
      const latestTodayAttendance = attendances
        .filter((a) => a.userId === currentSession?.user.userId && a.businessId === activeBusinessId && new Date(a.timestamp).toDateString() === today)
        .sort((a, b) => b.timestamp - a.timestamp)[0];
      const clockedIn = latestTodayAttendance?.type === 'MASUK';
      const clockedOut = latestTodayAttendance?.type === 'PULANG' || !latestTodayAttendance;"""
if new_transfer not in s:
    if old_transfer not in s:
        raise SystemExit("Cashier attendance session guard: stock-transfer guard anchor missing")
    s = s.replace(old_transfer, new_transfer, 1)

p.write_text(s, encoding="utf-8")
print("Cashier stock input now checks the latest attendance event for the same cashier, business, and local date.")
