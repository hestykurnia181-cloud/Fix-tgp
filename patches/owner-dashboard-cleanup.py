from pathlib import Path
p = Path("project/src/screens/OwnerDashboardScreen.tsx")
s = p.read_text()
for token in ("globalOwnerSales", "delete" + "OwnerSale", "Trash2", "ReceiptText"):
    s = s.replace("    " + token + ",\n", "")
    s = s.replace("  " + token + ",\n", "")
p.write_text(s)
print("Owner dashboard cleanup complete")
