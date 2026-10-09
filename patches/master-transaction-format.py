from pathlib import Path
p = Path("project/src/screens/MasterDashboardScreen.tsx")
s = p.read_text()
s = s.replace("formatRupiah(sale.totalAmount)", "new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(sale.totalAmount)")
p.write_text(s)
print("Master transaction currency formatting normalized")
