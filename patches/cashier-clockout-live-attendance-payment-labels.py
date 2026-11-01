from pathlib import Path

root = Path("project")

# 1) Fetch attendance and damaged reports from Supabase at the moment of clock-out.
service = root / "src/services/supabaseSyncService.ts"
s = service.read_text(encoding="utf-8")
anchor = "  public async fetchCashierClosingForShift(cashierUserId: string, businessId: string, shiftStartedAt: number): Promise<CashierClosingEntity | null> {"
methods = """  public async fetchAttendanceForLocalDay(userId: string, businessId: string, dayStart: number, dayEnd: number): Promise<AttendanceEntity[] | null> {
    const supabase = getSupabaseClient();
    if (!supabase || (typeof navigator !== 'undefined' && !navigator.onLine)) return null;
    const { data, error } = await supabase
      .from('attendances')
      .select('*')
      .eq('user_id', userId)
      .eq('business_id', businessId)
      .gte('timestamp', dayStart)
      .lt('timestamp', dayEnd)
      .order('timestamp', { ascending: false });
    if (error) throw error;
    return (data || []).map(mapAttendanceFromDb);
  }

  public async fetchDamagedReportsForShift(businessId: string, outletId: string, shiftStartedAt: number): Promise<DamagedGoodsReportEntity[] | null> {
    const supabase = getSupabaseClient();
    if (!supabase || (typeof navigator !== 'undefined' && !navigator.onLine)) return null;
    const { data, error } = await supabase
      .from('damaged_goods')
      .select('*')
      .eq('business_id', businessId)
      .eq('outlet_id', outletId)
      .gte('timestamp', shiftStartedAt);
    if (error) throw error;
    return (data || []).map(mapDamagedFromDb);
  }

"""
if "fetchAttendanceForLocalDay(" not in s:
    if anchor not in s:
        raise SystemExit("[armen-clockout] service insertion anchor missing")
    s = s.replace(anchor, methods + anchor, 1)
service.write_text(s, encoding="utf-8")

# 2) Do not disable the clock-out button based on a potentially stale local cache.
attendance = root / "src/screens/AttendanceScreen.tsx"
s = attendance.read_text(encoding="utf-8")
old = """            disabled={!hasClockedIn}
            data-testid="btn_clock_out""" 
new = """            data-testid="btn_clock_out"""
if new not in s:
    if old not in s:
        raise SystemExit("[armen-clockout] clock-out disabled attribute anchor missing")
    s = s.replace(old, new, 1)
attendance.write_text(s, encoding="utf-8")

# 3) Use server attendance as source of truth before accepting MASUK/PULANG.
context = root / "src/context/TgpContext.tsx"
s = context.read_text(encoding="utf-8")
old_validation = """    const todayKey = new Date().toDateString();
    const todayEvents = attendances
      .filter((a) => a.userId === currentSession.user.userId && a.businessId === activeBusinessId && new Date(a.timestamp).toDateString() === todayKey)
      .sort((a, b) => b.timestamp - a.timestamp);
    const latestTodayEvent = todayEvents[0];
    const checkInCountToday = todayEvents.filter((a) => a.type === 'MASUK').length;"""
new_validation = """    const now = new Date();
    const dayStartDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const dayStart = dayStartDate.getTime();
    const dayEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1).getTime();
    let serverTodayEvents: AttendanceEntity[] | null = null;
    try {
      serverTodayEvents = await supabaseSyncService.fetchAttendanceForLocalDay(currentSession.user.userId, activeBusinessId, dayStart, dayEnd);
    } catch (error: any) {
      setErrorMessage('Gagal memeriksa absensi terbaru dari server: ' + (error?.message || 'Kesalahan database') + '. Coba lagi saat koneksi stabil.');
      return false;
    }
    const localTodayEvents = attendances
      .filter((a) => a.userId === currentSession.user.userId && a.businessId === activeBusinessId && a.timestamp >= dayStart && a.timestamp < dayEnd);
    const todayEvents = (serverTodayEvents ?? localTodayEvents).sort((a, b) => b.timestamp - a.timestamp);
    if (serverTodayEvents) {
      const serverIds = new Set(serverTodayEvents.map((a) => a.attendanceId));
      setAttendances((prev) => [...serverTodayEvents!, ...prev.filter((a) => !(a.userId === currentSession.user.userId && a.businessId === activeBusinessId && a.timestamp >= dayStart && a.timestamp < dayEnd) && !serverIds.has(a.attendanceId))]);
    }
    const latestTodayEvent = todayEvents[0];
    const checkInCountToday = todayEvents.filter((a) => a.type === 'MASUK').length;"""
if new_validation not in s:
    if old_validation not in s:
        raise SystemExit("[armen-clockout] recordAttendance day validation anchor missing")
    s = s.replace(old_validation, new_validation, 1)

old_shift = "    const shiftStartedAt = getCurrentShiftStart(currentSession.user.userId, activeBusinessId);\n    let completedClosing: CashierClosingEntity | undefined;"
new_shift = "    const shiftStartedAt = type === 'PULANG' ? (latestTodayEvent?.type === 'MASUK' ? latestTodayEvent.timestamp : 0) : getCurrentShiftStart(currentSession.user.userId, activeBusinessId);\n    let completedClosing: CashierClosingEntity | undefined;"
if new_shift not in s:
    if old_shift not in s:
        raise SystemExit("[armen-clockout] shift start calculation anchor missing")
    s = s.replace(old_shift, new_shift, 1)

old_closing = """      completedClosing = cashierClosings.find((c) => c.cashierUserId === currentSession.user.userId && c.shiftStartedAt === shiftStartedAt && (c.status === 'READY_FOR_CLOCK_OUT' || c.status === 'COMPLETED'));
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
      if (!completedClosing) { setErrorMessage('Kasir wajib menyelesaikan closing sebelum absen pulang. Closing belum ditemukan di database.'); return false; }
      const pendingDamage = damagedReports.some((d) => d.businessId === activeBusinessId && d.outletId === currentSession.user.outletId && d.timestamp >= shiftStartedAt && d.status === DamagedStatus.PENDING);
      if (pendingDamage) { setErrorMessage('Absen pulang tertahan karena masih ada laporan cup rusak yang menunggu approval.'); return false; }"""
new_closing = """      try {
        completedClosing = await supabaseSyncService.fetchCashierClosingForShift(currentSession.user.userId, activeBusinessId, shiftStartedAt) || undefined;
      } catch (error: any) {
        const detail = error?.message || error?.details || error?.hint || 'Kesalahan database tidak diketahui.';
        setErrorMessage('Gagal memeriksa closing kasir: ' + detail + '. Silakan coba lagi.');
        return false;
      }
      if (!completedClosing && (!serverTodayEvents)) {
        completedClosing = cashierClosings.find((c) => c.cashierUserId === currentSession.user.userId && c.shiftStartedAt === shiftStartedAt && (c.status === 'READY_FOR_CLOCK_OUT' || c.status === 'COMPLETED'));
      }
      if (!completedClosing) { setErrorMessage('Kasir wajib menyelesaikan closing sebelum absen pulang. Closing untuk shift aktif tidak ditemukan di server.'); return false; }
      const verifiedClosing = completedClosing;
      setCashierClosings((prev) => prev.some((c) => c.closingId === verifiedClosing.closingId) ? prev : [verifiedClosing, ...prev]);
      let shiftDamageReports: DamagedGoodsReportEntity[] | null = null;
      try {
        shiftDamageReports = await supabaseSyncService.fetchDamagedReportsForShift(activeBusinessId, currentSession.user.outletId!, shiftStartedAt);
      } catch (error: any) {
        setErrorMessage('Gagal memeriksa approval barang rusak: ' + (error?.message || 'Kesalahan database') + '. Coba lagi.');
        return false;
      }
      const pendingDamage = (shiftDamageReports ?? damagedReports).some((d) => d.businessId === activeBusinessId && d.outletId === currentSession.user.outletId && d.timestamp >= shiftStartedAt && d.status === DamagedStatus.PENDING);
      if (pendingDamage) { setErrorMessage('Absen pulang tertahan karena masih ada laporan cup rusak yang menunggu approval.'); return false; }"""
if new_closing not in s:
    if old_closing not in s:
        raise SystemExit("[armen-clockout] closing/damage authoritative validation anchor missing")
    s = s.replace(old_closing, new_closing, 1)
context.write_text(s, encoding="utf-8")

# 4) Make closing history unmistakably payment-method based, never a global net-income field.
closing = root / "src/screens/CashierClosingScreen.tsx"
s = closing.read_text(encoding="utf-8")
s = s.replace("Cash bersih {rupiah(getPaymentBreakdown(c).cashNet)} · QRIS {rupiah(getPaymentBreakdown(c).qris)} · TF {rupiah(getPaymentBreakdown(c).transfer)}",
              "Cash masuk {rupiah(getPaymentBreakdown(c).cash)} · QRIS {rupiah(getPaymentBreakdown(c).qris)} · Transfer {rupiah(getPaymentBreakdown(c).transfer)} · Debit {rupiah(getPaymentBreakdown(c).debit)}", 1)
s = s.replace("['Cash sebelum pengeluaran',rupiah(b.cash)],['Pengeluaran (potong Cash)',rupiah(b.expense)],['Cash setelah pengeluaran',rupiah(b.cashNet)]",
              "['Cash masuk',rupiah(b.cash)],['Pengeluaran (mengurangi Cash)',rupiah(b.expense)],['Sisa Cash',rupiah(b.cashNet)]", 1)
s = s.replace("['Cash sebelum pengeluaran',monthlyPayments.cash],['Pengeluaran (potong Cash)',monthlyPayments.expense],['Cash setelah pengeluaran',monthlyPayments.cashNet]",
              "['Cash masuk',monthlyPayments.cash],['Pengeluaran (mengurangi Cash)',monthlyPayments.expense],['Sisa Cash',monthlyPayments.cashNet]", 1)
closing.write_text(s, encoding="utf-8")

# Remove the misleading global net figure from the cashier closing audit description.
old_audit = "addAuditLog('CASHIER_CLOSING_CREATED', `Closing ${outlet.name} oleh ${currentSession.user.fullName}; bersih Rp ${closing.netIncome.toLocaleString('id-ID')}`, activeBusinessId);"
new_audit = "addAuditLog('CASHIER_CLOSING_CREATED', `Closing ${outlet.name} oleh ${currentSession.user.fullName}; rincian pembayaran tersimpan per metode`, activeBusinessId);"
if old_audit in s:
    s = s.replace(old_audit, new_audit, 1)
    context.write_text(s, encoding="utf-8")

# 5) Ensure installed PWAs promptly check for the latest deployed bundle.
main = root / "src/main.tsx"
s = main.read_text(encoding="utf-8")
old_sw = """if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch((error) => {
      console.warn('TGP PWA service worker registration failed:', error);
    });
  });
}"""
new_sw = """if ('serviceWorker' in navigator && import.meta.env.PROD) {
  let refreshingForWorker = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (refreshingForWorker) return;
    refreshingForWorker = true;
    window.location.reload();
  });
  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`, { updateViaCache: 'none' });
      await registration.update();
    } catch (error) {
      console.warn('TGP PWA service worker registration/update failed:', error);
    }
  });
}"""
if new_sw not in s:
    if old_sw not in s:
        raise SystemExit("[armen-clockout] service worker registration anchor missing")
    s = s.replace(old_sw, new_sw, 1)
main.write_text(s, encoding="utf-8")

sw = root / "public/sw.js"
s = sw.read_text(encoding="utf-8")
s = s.replace("const CACHE_VERSION = 'tgp-management-v2';", "const CACHE_VERSION = 'tgp-management-v3';", 1)
sw.write_text(s, encoding="utf-8")

print("[armen-clockout] clock-out now uses fresh server attendance, closing and damage approval; closing history is payment-method based; PWA forces update checks.")
