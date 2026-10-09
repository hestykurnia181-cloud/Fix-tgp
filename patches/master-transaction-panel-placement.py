from pathlib import Path

p = Path("project/src/screens/MasterDashboardScreen.tsx")
s = p.read_text()

start_marker = '      <section className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">\n        <div className="flex items-center justify-between gap-3">\n          <div><h3 className="text-base font-extrabold text-slate-900 flex items-center gap-2"><ReceiptText'
start = s.find(start_marker)
if start < 0:
    # It may already have been moved by an earlier run.
    if s.find('Riwayat Transaksi Penjualan') >= 0 and s.find('Riwayat Transaksi Penjualan') < s.find('Management Navigation Tabs'):
        print("Master transaction panel already placed near the top")
        raise SystemExit(0)
    raise RuntimeError("Master transaction panel start not found")

end_marker = '      </section>\n\n      <CreateBusinessDialog'
end = s.find(end_marker, start)
if end < 0:
    raise RuntimeError("Master transaction panel end not found")
end += len('      </section>\n\n')
panel = s[start:end]
s = s[:start] + s[end:]

anchor = '      {/* Management Navigation Tabs */}'
if anchor not in s:
    raise RuntimeError("Management Navigation Tabs anchor not found")
s = s.replace(anchor, panel + anchor, 1)
p.write_text(s)
print("Master transaction panel moved directly below platform metrics, before management tabs")
