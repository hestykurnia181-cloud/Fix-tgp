from pathlib import Path
import re

ROOT = Path("project")

def require_replace(path, old, new, label):
    p = ROOT / path
    s = p.read_text()
    if new in s:
        print("[attendance-storage] already applied:", label)
        return
    if old not in s:
        raise RuntimeError("[attendance-storage] anchor missing: " + label + " (" + path + ")")
    p.write_text(s.replace(old, new, 1))

# Storage service: photos become small public URLs in the attendance row.
service = ROOT / "src/services/supabaseSyncService.ts"
s = service.read_text()
if "public async uploadAttendancePhoto(" not in s:
    marker = "\n  public async sync"
    idx = s.find(marker)
    if idx < 0:
        raise RuntimeError("[attendance-storage] sync method insertion point missing")
    methods = r"""

  public async uploadAttendancePhoto(dataUrl: string, businessId: string, userId: string, timestamp: number): Promise<string> {
    const supabase = getSupabaseClient();
    if (!supabase) throw new Error('Koneksi Supabase belum tersedia');
    if (!dataUrl || !dataUrl.startsWith('data:image/')) throw new Error('Format foto absensi tidak valid');
    const response = await fetch(dataUrl);
    const blob = await response.blob();
    if (blob.size > 1024 * 1024) throw new Error('Ukuran foto absensi melebihi 1 MB');
    const extension = blob.type === 'image/png' ? 'png' : blob.type === 'image/webp' ? 'webp' : 'jpg';
    const safeBusiness = String(businessId || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '_');
    const safeUser = String(userId || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '_');
    const path = safeBusiness + '/' + safeUser + '/' + String(timestamp) + '.' + extension;
    const { error } = await supabase.storage.from('attendance-photos').upload(path, blob, {
      contentType: blob.type || 'image/jpeg', upsert: true, cacheControl: '31536000'
    });
    if (error) throw error;
    const { data } = supabase.storage.from('attendance-photos').getPublicUrl(path);
    return data.publicUrl;
  }

  public async migrateAttendancePhotos(rows: any[]) {
    const supabase = getSupabaseClient();
    if (!supabase || !Array.isArray(rows) || (typeof navigator !== 'undefined' && !navigator.onLine)) return;
    const prefix = '__TGP_ATTENDANCE_PHOTO__';
    for (const row of rows) {
      const raw = String(row?.note || '');
      if (!raw.startsWith(prefix)) continue;
      let parsed: any;
      try { parsed = JSON.parse(raw.slice(prefix.length)); } catch { continue; }
      const photo = String(parsed?.photo || '');
      if (!photo.startsWith('data:image/')) continue;
      const attendanceId = String(row.attendanceId || row.attendance_id || row.id || '');
      if (!attendanceId) continue;
      try {
        const url = await this.uploadAttendancePhoto(photo, String(row.businessId || row.business_id || ''), String(row.userId || row.user_id || ''), Number(row.timestamp || Date.now()));
        const nextNote = prefix + JSON.stringify({ note: String(parsed.note || ''), photo: url });
        const { error } = await supabase.from('attendances').update({ note: nextNote }).eq('attendance_id', attendanceId);
        if (error) throw error;
        console.log('[attendance-storage] migrated photo', attendanceId);
      } catch (error) {
        console.warn('[attendance-storage] photo migration failed', attendanceId, error);
      }
    }
  }
"""
    service.write_text(s[:idx] + methods + s[idx:])
    print("[attendance-storage] added Storage upload and legacy migration methods")

# New attendance photo uploads are completed before the attendance row is persisted.
ctx = ROOT / "src/context/TgpContext.tsx"
s = ctx.read_text()
s2 = s.replace(
    "  const recordAttendance = (type: 'MASUK' | 'PULANG', note: string, photoDataUrl?: string) => {",
    "  const recordAttendance = async (type: 'MASUK' | 'PULANG', note: string, photoDataUrl?: string) => {",
    1
)
if s2 == s and "const recordAttendance = async (type: 'MASUK' | 'PULANG', note: string, photoDataUrl?: string)" not in s:
    raise RuntimeError("[attendance-storage] recordAttendance implementation anchor missing")
s = s2
if "const attendancePhotoUrl = photoDataUrl" not in s:
    pattern = r"(  const recordAttendance = async \(type: 'MASUK' \| 'PULANG', note: string, photoDataUrl\?: string\) => \{\n)"
    m = re.search(pattern, s)
    if not m: raise RuntimeError("[attendance-storage] async recorder body anchor missing")
    insert = """    let attendancePhotoUrl = '';
    if (photoDataUrl) {
      try {
        attendancePhotoUrl = await supabaseSyncService.uploadAttendancePhoto(
          photoDataUrl, activeBusiness?.businessId || '', '', Date.now()
        );
      } catch (error) {
        console.error('[attendance-storage] photo upload failed; attendance will be saved without embedded image', error);
      }
    }
"""
    s = s[:m.end()] + insert + s[m.end():]
old_note = """      note: photoDataUrl
        ? '__TGP_ATTENDANCE_PHOTO__' + JSON.stringify({ note: note.trim(), photo: photoDataUrl })
        : note.trim(),"""
new_note = """      note: attendancePhotoUrl
        ? '__TGP_ATTENDANCE_PHOTO__' + JSON.stringify({ note: note.trim(), photo: attendancePhotoUrl })
        : note.trim(),"""
if new_note not in s:
    if old_note not in s: raise RuntimeError("[attendance-storage] attendance note encoding anchor missing")
    s = s.replace(old_note, new_note, 1)
ctx.write_text(s)
print("[attendance-storage] new check-in/out photos now upload before attendance sync")

# Owner/Admin attendance report migrates older Base64 rows in the currently selected business.
report = ROOT / "src/screens/EmployeeManagementScreen.tsx"
rs = report.read_text()
if "supabaseSyncService.migrateAttendancePhotos" not in rs:
    import_line = "import { supabaseSyncService } from '../services/supabaseSyncService';\n"
    if import_line not in rs:
        # Insert after the existing import block.
        matches = list(re.finditer(r"^import .*?;\s*$", rs, re.M))
        if not matches: raise RuntimeError("[attendance-storage] report import block missing")
        pos = matches[-1].end()
        rs = rs[:pos] + "\n" + import_line + rs[pos:]
    # Insert a migration effect after businessAttendance is defined, avoiding assumptions about context destructuring.
    marker = "  const attendanceSummary = useMemo(() => {"
    effect = """  useEffect(() => {
    if (businessAttendance.length) {
      void supabaseSyncService.migrateAttendancePhotos(businessAttendance);
    }
  }, [businessAttendance]);

"""
    if marker not in rs: raise RuntimeError("[attendance-storage] report migration effect anchor missing")
    rs = rs.replace(marker, effect + marker, 1)
    report.write_text(rs)

# Ensure the screen imports the React hook used by the migration effect.
lines = rs.splitlines()
for i, line in enumerate(lines):
    if line.startswith("import") and ("from 'react'" in line or 'from "react"' in line):
        if "useEffect" not in line:
            if "{" in line:
                lines[i] = line.replace("{", "{ useEffect,", 1)
            else:
                lines.insert(i + 1, "import { useEffect } from 'react';")
        break
rs = "\n".join(lines) + "\n"
report.write_text(rs)
print("[attendance-storage] Owner/Admin attendance view migrates legacy Base64 photos to Storage")
