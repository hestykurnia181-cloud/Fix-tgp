from pathlib import Path
import re

ROOT = Path("project")

def replace(path, old, new, label):
    p = ROOT / path
    s = p.read_text()
    if new in s:
        print("[attendance-daily-photo] already applied:", label)
        return
    if old not in s:
        raise RuntimeError("[attendance-daily-photo] anchor missing: " + label + " (" + path + ")")
    p.write_text(s.replace(old, new, 1))

# The existing attendance table already syncs its note field. Store a compressed photo
# inside a tagged JSON note so no schema migration / unknown column is required.
replace(
    "src/context/TgpContext.tsx",
    "  recordAttendance: (type: 'MASUK' | 'PULANG', note: string) => void;",
    "  recordAttendance: (type: 'MASUK' | 'PULANG', note: string, photoDataUrl?: string) => void;",
    "attendance context contract"
)
replace(
    "src/context/TgpContext.tsx",
    "  const recordAttendance = (type: 'MASUK' | 'PULANG', note: string) => {",
    "  const recordAttendance = (type: 'MASUK' | 'PULANG', note: string, photoDataUrl?: string) => {",
    "attendance recorder signature"
)
replace(
    "src/context/TgpContext.tsx",
    "      note: note.trim(),\n    };\n\n    setAttendances((prev) => [newAtt, ...prev]);",
    """      note: photoDataUrl
        ? '__TGP_ATTENDANCE_PHOTO__' + JSON.stringify({ note: note.trim(), photo: photoDataUrl })
        : note.trim(),
    };

    setAttendances((prev) => [newAtt, ...prev]);""",
    "persist photo in synced attendance note"
)

# Compress the captured photo to keep the synced note small enough for normal mobile networks.
service = ROOT / "src/screens/ServiceStaffScreen.tsx"
s = service.read_text()
helper = """const compressAttendancePhoto = async (file: File): Promise<string> => {
 try {
   const bitmap = await createImageBitmap(file);
   const scale = Math.min(1, 800 / Math.max(bitmap.width, bitmap.height));
   const canvas = document.createElement('canvas');
   canvas.width = Math.max(1, Math.round(bitmap.width * scale));
   canvas.height = Math.max(1, Math.round(bitmap.height * scale));
   const ctx = canvas.getContext('2d');
   if (!ctx) throw new Error('Canvas tidak tersedia');
   ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
   bitmap.close();
   return canvas.toDataURL('image/jpeg', 0.62);
 } catch {
   return await new Promise<string>((resolve, reject) => {
     const reader = new FileReader();
     reader.onload = () => resolve(String(reader.result || ''));
     reader.onerror = () => reject(new Error('Foto gagal dibaca'));
     reader.readAsDataURL(file);
   });
 }
};
"""
if "const compressAttendancePhoto = async" not in s:
    anchor = "const money=(n:number)=>'Rp '+Math.round(n).toLocaleString('id-ID');\n"
    if anchor not in s:
        raise RuntimeError("[attendance-daily-photo] helper insertion anchor missing (ServiceStaffScreen.tsx)")
    s = s.replace(anchor, anchor + helper, 1)

old = """   const reader=new FileReader();
   reader.onload=()=>{
     const dk=dateKey(new Date());
     const old=readAttendance().find(a=>a.userId===user.userId&&a.businessId===activeBusiness.businessId&&a.dateKey===dk);
     const row:Attendance=old||{id:'att-'+user.userId+'-'+dk,userId:user.userId,businessId:activeBusiness.businessId,dateKey:dk};
     if(target==='IN'){row.checkInAt=Date.now();row.checkInPhoto=String(reader.result||'')}
     else {row.checkOutAt=Date.now();row.checkOutPhoto=String(reader.result||'')}
     const next=[...readAttendance().filter(a=>a.id!==row.id),row];try{saveAttendance(next)}catch(storageError){console.warn('[attendance] photo cache unavailable; syncing attendance timestamp anyway',storageError)}setAttendance(next);
      // Persist attendance to the shared Supabase-backed attendance stream so Owner/Admin Owner reports see it on every device.
      recordAttendance(target==='IN'?'MASUK':'PULANG',target==='IN'?'Absensi masuk (foto diambil)':'Absensi pulang (foto diambil)');
      setTarget(null);e.target.value='';
   };
   reader.readAsDataURL(file);"""
new = """   compressAttendancePhoto(file).then((photo)=>{
     const dk=dateKey(new Date());
     const old=readAttendance().find(a=>a.userId===user.userId&&a.businessId===activeBusiness.businessId&&a.dateKey===dk);
     const row:Attendance=old||{id:'att-'+user.userId+'-'+dk,userId:user.userId,businessId:activeBusiness.businessId,dateKey:dk};
     if(target==='IN'){row.checkInAt=Date.now();row.checkInPhoto=photo}
     else {row.checkOutAt=Date.now();row.checkOutPhoto=photo}
     const next=[...readAttendance().filter(a=>a.id!==row.id),row];try{saveAttendance(next)}catch(storageError){console.warn('[attendance] photo cache unavailable; syncing attendance timestamp anyway',storageError)}setAttendance(next);
     // Save the compressed photo into the Supabase-synced attendance record for Owner cross-device reports.
     recordAttendance(target==='IN'?'MASUK':'PULANG',target==='IN'?'Absensi masuk':'Absensi pulang',photo);
     setTarget(null);e.target.value='';
   }).catch((error)=>{console.error('[attendance] photo processing failed',error);window.alert('Foto absensi gagal diproses. Silakan coba lagi.');setTarget(null);e.target.value=''});"""
if new not in s:
    if old not in s:
        raise RuntimeError("[attendance-daily-photo] photo capture anchor missing (ServiceStaffScreen.tsx)")
    s = s.replace(old, new, 1)
service.write_text(s)

# Daily Owner report: select a date, list only that date, and expose synced check-in/out photos.
p = ROOT / "src/screens/EmployeeManagementScreen.tsx"
s = p.read_text()
if "selectedAttendanceDate" not in s:
    s = s.replace(
        "  const [tab, setTab] = useState<'employees' | 'attendance'>('employees');",
        "  const [tab, setTab] = useState<'employees' | 'attendance'>('employees');\n  const [selectedAttendanceDate, setSelectedAttendanceDate] = useState(() => { const d = new Date(); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); });\n  const [selectedAttendancePhoto, setSelectedAttendancePhoto] = useState<string | null>(null);",
        1
    )
anchor = "  const attendanceSummary = useMemo(() => {"
daily = """  const dailyAttendance = useMemo(() => businessAttendance.filter((a) => {
    const d = new Date(a.timestamp);
    const key = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    return key === selectedAttendanceDate;
  }), [businessAttendance, selectedAttendanceDate]);

  const parseAttendanceNote = (note: string) => {
    const prefix = '__TGP_ATTENDANCE_PHOTO__';
    if (!note?.startsWith(prefix)) return { note: note || 'Tanpa catatan', photo: '' };
    try {
      const parsed = JSON.parse(note.slice(prefix.length));
      return { note: parsed.note || 'Absensi foto', photo: typeof parsed.photo === 'string' ? parsed.photo : '' };
    } catch {
      return { note: 'Absensi foto', photo: '' };
    }
  };

"""
if "const dailyAttendance = useMemo" not in s:
    if anchor not in s:
        raise RuntimeError("[attendance-daily-photo] daily attendance insertion anchor missing")
    s = s.replace(anchor, daily + anchor, 1)

old_history = """            <div className="pt-2 border-t border-slate-100 space-y-2">
              <div className="text-xs font-extrabold uppercase tracking-wider text-slate-500">Riwayat Terbaru</div>
              {businessAttendance.slice(0, 30).map((a) => <div key={a.attendanceId} className="flex items-center justify-between p-3 rounded-xl bg-white border border-slate-100 text-xs"><div><p className="font-bold text-slate-900">{a.userName}</p><p className="text-[10px] text-slate-400">{fmtDate(a.timestamp)} • {a.note || 'Tanpa catatan'}</p></div><div className="text-right"><span className={`font-extrabold ${a.type === 'MASUK' ? 'text-emerald-600' : 'text-orange-600'}`}>{a.type}</span><span className="block text-[10px] text-slate-400">{fmtTime(a.timestamp)}</span></div></div>)}
            </div>"""
new_history = """            <div className="pt-3 border-t border-slate-100 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <div className="text-xs font-extrabold uppercase tracking-wider text-slate-700">Laporan Presensi Harian</div>
                  <p className="text-[10px] text-slate-500 mt-1">Data dipisahkan berdasarkan tanggal. Foto masuk/pulang yang tersinkron ditampilkan di sini.</p>
                </div>
                <input aria-label="Tanggal laporan presensi" type="date" value={selectedAttendanceDate} onChange={(e) => setSelectedAttendanceDate(e.target.value)} className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs font-bold" />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-xl bg-slate-50 p-3"><p className="text-[10px] text-slate-500">Total presensi</p><p className="text-lg font-black text-slate-900">{dailyAttendance.length}</p></div>
                <div className="rounded-xl bg-emerald-50 p-3"><p className="text-[10px] text-emerald-700">Masuk</p><p className="text-lg font-black text-emerald-800">{dailyAttendance.filter((a) => a.type === 'MASUK').length}</p></div>
                <div className="rounded-xl bg-orange-50 p-3"><p className="text-[10px] text-orange-700">Pulang</p><p className="text-lg font-black text-orange-800">{dailyAttendance.filter((a) => a.type === 'PULANG').length}</p></div>
              </div>
              {dailyAttendance.length === 0 ? <p className="py-8 text-center text-xs text-slate-400">Tidak ada presensi pada tanggal {new Date(selectedAttendanceDate + 'T12:00:00').toLocaleDateString('id-ID')}.</p> : dailyAttendance.map((a) => {
                const parsed = parseAttendanceNote(a.note);
                return <div key={a.attendanceId} className="p-3 rounded-2xl bg-white border border-slate-100 flex flex-col sm:flex-row sm:items-center gap-3 text-xs" data-testid={'daily_attendance_' + a.attendanceId}>
                  <div className="flex-1 min-w-0">
                    <p className="font-extrabold text-slate-900">{a.userName}</p>
                    <p className="text-[10px] text-slate-500 mt-1">{new Date(a.timestamp).toLocaleDateString('id-ID')} • {fmtTime(a.timestamp)} • {parsed.note}</p>
                    <span className={`inline-flex mt-2 px-2 py-1 rounded-lg font-extrabold ${a.type === 'MASUK' ? 'bg-emerald-50 text-emerald-700' : 'bg-orange-50 text-orange-700'}`}>{a.type === 'MASUK' ? 'ABSEN MASUK' : 'ABSEN PULANG'}</span>
                  </div>
                  {parsed.photo ? <button type="button" onClick={() => setSelectedAttendancePhoto(parsed.photo)} className="self-start rounded-xl overflow-hidden border border-slate-200 focus:ring-2 focus:ring-indigo-500" aria-label={'Lihat foto presensi ' + a.userName}><img src={parsed.photo} alt={'Foto presensi ' + a.userName} loading="lazy" className="w-20 h-20 object-cover" /><span className="block text-[9px] font-bold text-center bg-slate-50 py-1">Lihat foto</span></button> : <div className="w-20 h-20 rounded-xl border border-dashed border-slate-200 flex items-center justify-center text-[9px] text-slate-400 text-center px-1">Foto belum tersinkron</div>}
                </div>;
              })}
            </div>
            {selectedAttendancePhoto && <div className="fixed inset-0 z-[100] bg-black/80 flex items-center justify-center p-4" role="dialog" aria-modal="true" onClick={() => setSelectedAttendancePhoto(null)}><div className="max-w-3xl max-h-[90vh]" onClick={(e) => e.stopPropagation()}><button type="button" onClick={() => setSelectedAttendancePhoto(null)} className="mb-2 px-4 py-2 rounded-xl bg-white text-slate-900 text-xs font-extrabold">Tutup foto</button><img src={selectedAttendancePhoto} alt="Foto presensi ukuran penuh" className="max-h-[80vh] max-w-full rounded-2xl object-contain bg-white" /></div></div>}"""
if new_history not in s:
    if old_history not in s:
        raise RuntimeError("[attendance-daily-photo] report history block anchor missing")
    s = s.replace(old_history, new_history, 1)
p.write_text(s)
print("[attendance-daily-photo] daily Owner report and cross-device photo sync patch applied")
