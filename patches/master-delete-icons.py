from pathlib import Path
p = Path("project/src/screens/MasterDashboardScreen.tsx")
s = p.read_text()
if "  Trash2," not in s or "  ReceiptText," not in s:
    anchor = "  Users,\n"
    if anchor not in s:
        raise RuntimeError("Master icon import anchor missing")
    s = s.replace(anchor, anchor + "  Trash2,\n  ReceiptText,\n", 1)
    p.write_text(s)
print("Master icons ready")
