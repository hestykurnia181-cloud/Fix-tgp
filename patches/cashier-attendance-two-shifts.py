from pathlib import Path

root = Path("project")

# Attendance screen: permit a second shift only after the first shift has been clocked out.
attendance = root / "src/screens/AttendanceScreen.tsx"
s = attendance.read_text(encoding="utf-8")
old = """  const hasClockedIn = myAttendancesToday.some((a) => a.type === 'MASUK');
  const hasClockedOut = myAttendancesToday.some((a) => a.type === 'PULANG');
  const latestClockIn = myAttendancesToday.filter((a)=>a.type==='MASUK').sort((a,b)=>b.timestamp-a.timestamp)[0];"""
new = """  const latestTodayAttendance = [...myAttendancesToday].sort((a, b) => b.timestamp - a.timestamp)[0];
  const checkInCountToday = myAttendancesToday.filter((a) => a.type === 'MASUK').length;
  const canClockIn = checkInCountToday < 2 && latestTodayAttendance?.type !== 'MASUK';
  const hasClockedIn = latestTodayAttendance?.type === 'MASUK';
  const hasClockedOut = latestTodayAttendance?.type === 'PULANG';
  const latestClockIn = myAttendancesToday.filter((a)=>a.type==='MASUK').sort((a,b)=>b.timestamp-a.timestamp)[0];"""
if new not in s:
    if old not in s:
        raise SystemExit("[two-shifts] AttendanceScreen state anchor missing")
    s = s.replace(old, new, 1)

s = s.replace("disabled={hasClockedIn}", "disabled={!canClockIn}", 1)
s = s.replace(
    "<span>{hasClockedIn ? 'Sudah Masuk' : 'Absen Masuk'}</span>",
    "<span>{canClockIn ? 'Absen Masuk' : checkInCountToday >= 2 ? 'Batas 2 Shift' : 'Sudah Masuk'}</span>",
    1
)
s = s.replace(
    "disabled={!hasClockedIn || hasClockedOut || (requiresClosing && !hasClosing)}",
    "disabled={!hasClockedIn || (requiresClosing && !hasClosing)}",
    1
)
attendance.write_text(s, encoding="utf-8")

# Context boundary: enforce alternating IN/OUT events and a maximum of two check-ins per local day.
context = root / "src/context/TgpContext.tsx"
s = context.read_text(encoding="utf-8")
anchor = """    if (!photoDataUrl || !photoDataUrl.startsWith('data:image/')) { setErrorMessage('Foto wajib dilampirkan untuk absensi.'); return false; }
    const role = normalizeUserRole(currentSession.user.role);"""
replacement = """    if (!photoDataUrl || !photoDataUrl.startsWith('data:image/')) { setErrorMessage('Foto wajib dilampirkan untuk absensi.'); return false; }
    const todayKey = new Date().toDateString();
    const todayEvents = attendances
      .filter((a) => a.userId === currentSession.user.userId && a.businessId === activeBusinessId && new Date(a.timestamp).toDateString() === todayKey)
      .sort((a, b) => b.timestamp - a.timestamp);
    const latestTodayEvent = todayEvents[0];
    const checkInCountToday = todayEvents.filter((a) => a.type === 'MASUK').length;
    if (type === 'MASUK') {
      if (latestTodayEvent?.type === 'MASUK') { setErrorMessage('Anda masih tercatat bekerja. Absen pulang terlebih dahulu sebelum memulai shift berikutnya.'); return false; }
      if (checkInCountToday >= 2) { setErrorMessage('Batas absensi masuk adalah 2 kali dalam satu hari.'); return false; }
    } else if (latestTodayEvent?.type !== 'MASUK') {
      setErrorMessage('Absen pulang hanya dapat dilakukan setelah absen masuk pada shift yang sedang aktif.');
      return false;
    }
    const role = normalizeUserRole(currentSession.user.role);"""
if replacement not in s:
    if anchor not in s:
        raise SystemExit("[two-shifts] recordAttendance validation anchor missing")
    s = s.replace(anchor, replacement, 1)
context.write_text(s, encoding="utf-8")
print("[two-shifts] AttendanceScreen allows up to two alternating daily shifts; recordAttendance enforces the same rule.")
