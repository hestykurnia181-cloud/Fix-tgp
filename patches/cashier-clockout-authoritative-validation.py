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

service = root / "src/services/supabaseSyncService.ts"
service_source = service.read_text(encoding="utf-8")
service_anchor = "  public async finalizeCashierStockReturn(closingId: string, performedBy: string): Promise<any | null> {"
service_method = """  public async fetchCashierClosingForShift(cashierUserId: string, businessId: string, shiftStartedAt: number): Promise<CashierClosingEntity | null> {
    const supabase = getSupabaseClient();
    if (!supabase) return null;
    const { data, error } = await supabase
      .from('cashier_closings')
      .select('*')
      .eq('cashier_user_id', cashierUserId)
      .eq('business_id', businessId)
      .eq('shift_started_at', shiftStartedAt)
      .in('status', ['READY_FOR_CLOCK_OUT', 'COMPLETED'])
      .maybeSingle();
    if (error) throw error;
    return data ? mapCashierClosingFromDb(data) : null;
  }

"""
if "fetchCashierClosingForShift(" not in service_source:
    if service_anchor not in service_source:
        raise SystemExit("[clockout-gate] closing fetch insertion anchor missing")
    service_source = service_source.replace(service_anchor, service_method + service_anchor, 1)
    service.write_text(service_source, encoding="utf-8")

context = root / "src/context/TgpContext.tsx"
s = context.read_text(encoding="utf-8")
old_closing = """      completedClosing = cashierClosings.find((c) => c.cashierUserId === currentSession.user.userId && c.shiftStartedAt === shiftStartedAt && (c.status === 'READY_FOR_CLOCK_OUT' || c.status === 'COMPLETED'));
      if (!completedClosing) { setErrorMessage('Kasir wajib menyelesaikan closing sebelum absen pulang.'); return false; }"""
new_closing = """      completedClosing = cashierClosings.find((c) => c.cashierUserId === currentSession.user.userId && c.shiftStartedAt === shiftStartedAt && (c.status === 'READY_FOR_CLOCK_OUT' || c.status === 'COMPLETED'));
      if (!completedClosing) {
        try {
          completedClosing = await supabaseSyncService.fetchCashierClosingForShift(currentSession.user.userId, activeBusinessId, shiftStartedAt);
        } catch (error: any) {
          const detail = error?.message || error?.details || error?.hint || 'Kesalahan database tidak diketahui.';
          setErrorMessage('Gagal memeriksa closing kasir: ' + detail + '. Silakan coba lagi.');
          return false;
        }
        if (completedClosing) {
          const verifiedClosing = completedClosing;
          setCashierClosings((prev) => prev.some((c) => c.closingId === verifiedClosing.closingId) ? prev : [verifiedClosing, ...prev]);
        }
      }
      if (!completedClosing) { setErrorMessage('Kasir wajib menyelesaikan closing sebelum absen pulang. Closing belum ditemukan di database.'); return false; }"""
if new_closing not in s:
    if old_closing not in s:
        raise SystemExit("[clockout-gate] closing cache fallback anchor missing")
    s = s.replace(old_closing, new_closing, 1)
lines = s.splitlines()
for index, line in enumerate(lines):
    marker = "const serverReturn = await supabaseSyncService.finalizeCashierStockReturn("
    if marker in line:
        indent = line[:len(line) - len(line.lstrip())]
        args = line.split(marker, 1)[1].rsplit(");", 1)[0]
        lines[index:index + 1] = [
            indent + "let serverReturn: any = null;",
            indent + "try {",
            indent + "  serverReturn = await supabaseSyncService.finalizeCashierStockReturn(" + args + ");",
            indent + "} catch (error: any) {",
            indent + "  const detail = error?.message || error?.details || error?.hint || 'Kesalahan database tidak diketahui.';",
            indent + "  setErrorMessage('Pengembalian stok STAN gagal: ' + detail + ' Absensi pulang belum dicatat. Silakan coba lagi atau hubungi Admin.');",
            indent + "  return false;",
            indent + "}",
        ]
        s = "\n".join(lines) + "\n"
        break
else:
    if "let serverReturn: any = null;" not in s:
        raise SystemExit("[clockout-gate] stock return RPC anchor missing")
context.write_text(s, encoding="utf-8")
print("[clockout-gate] clock-out button no longer depends on potentially stale client closing cache; recordAttendance remains authoritative and reports stock-return RPC errors.")
