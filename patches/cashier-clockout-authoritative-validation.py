from pathlib import Path

root = Path("project")

attendance = root / "src/screens/AttendanceScreen.tsx"
s = attendance.read_text(encoding="utf-8")

old_today = """  const myAttendancesToday = activeAttendances.filter((a) => {
    const isToday = new Date(a.timestamp).toDateString() === new Date().toDateString();
    return isToday && a.userId === currentSession?.user.userId;
  });"""
new_today = """  const myAttendancesToday = activeAttendances.filter((a) => {
    const isToday = new Date(a.timestamp).toDateString() === new Date().toDateString();
    return isToday && a.userId === currentSession?.user.userId && a.businessId === activeBusiness?.businessId;
  });"""
if new_today not in s:
    if old_today not in s:
        raise SystemExit("[clockout-gate] today's attendance filter anchor missing")
    s = s.replace(old_today, new_today, 1)

old_closing_gate = """  const requiresClosing = currentSession?.user.role === UserRole.KASIR && activeBusiness?.templateType === 'FNB' && !!currentSession.user.outletId;
  const hasClosing = !!latestClockIn && cashierClosings.some((c)=>c.cashierUserId===currentSession?.user.userId && c.shiftStartedAt===latestClockIn.timestamp && c.status==='READY_FOR_CLOCK_OUT');"""
if old_closing_gate in s:
    s = s.replace(old_closing_gate, "", 1)
elif "const requiresClosing =" in s or "const hasClosing =" in s:
    raise SystemExit("[clockout-gate] closing gate declarations changed unexpectedly")

old_disabled = "disabled={!hasClockedIn || (requiresClosing && !hasClosing)}"
new_disabled = "disabled={!hasClockedIn}"
if new_disabled not in s:
    if old_disabled not in s:
        raise SystemExit("[clockout-gate] clock-out disabled condition anchor missing")
    s = s.replace(old_disabled, new_disabled, 1)

old_label = "{hasClockedOut ? 'Sudah Pulang' : requiresClosing && !hasClosing ? 'Wajib Closing Dulu' : 'Absen Pulang'}"
new_label = "{hasClockedOut ? 'Sudah Pulang' : 'Absen Pulang'}"
if new_label not in s:
    if old_label not in s:
        raise SystemExit("[clockout-gate] clock-out button label anchor missing")
    s = s.replace(old_label, new_label, 1)

s = s.replace("    cashierClosings,\n", "", 1)
s = s.replace("  const latestClockIn = myAttendancesToday.filter((a)=>a.type==='MASUK').sort((a,b)=>b.timestamp-a.timestamp)[0];\n", "", 1)
s = s.replace("import { UserRole } from '../types';\n", "", 1)

attendance.write_text(s, encoding="utf-8")

context = root / "src/context/TgpContext.tsx"
s = context.read_text(encoding="utf-8")
old_rpc = """      const serverReturn = await supabaseSyncService.finalizeCashierStockReturn(completedClosing.closingId, currentSession.user.fullName);
      const returnedByItem = new Map<string, number>(remainingStocks.map((s): [string, number] => [s.itemId,s.stockQuantity]));"""
new_rpc = """      let serverReturn: any = null;
      try {
        serverReturn = await supabaseSyncService.finalizeCashierStockReturn(completedClosing.closingId, currentSession.user.fullName);
      } catch (error: any) {
        const detail = error?.message || error?.details || error?.hint || 'Kesalahan database tidak diketahui.';
        setErrorMessage('Pengembalian stok STAN gagal: ' + detail + ' Absensi pulang belum dicatat. Silakan coba lagi atau hubungi Admin.');
        return false;
      }
      const returnedByItem = new Map<string, number>(remainingStocks.map((s): [string, number] => [s.itemId,s.stockQuantity]));"""
if new_rpc not in s:
    if "let serverReturn: any = null;" not in s:
        raise SystemExit("[clockout-gate] stock return RPC anchor missing")
else:
    s = s.replace(old_rpc, new_rpc, 1)

context.write_text(s, encoding="utf-8")
print("[clockout-gate] clock-out button no longer depends on potentially stale client closing cache; recordAttendance remains authoritative and reports stock-return RPC errors.")
