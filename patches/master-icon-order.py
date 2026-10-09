import re
from pathlib import Path
p = Path("project/src/screens/MasterDashboardScreen.tsx")
s = p.read_text()
pattern = r"import\s*\{([^}]*)\}\s*from\s*(['\"]lucide-react['\"]);"
m = re.search(pattern, s, re.S)
if not m:
    raise RuntimeError("lucide-react import block missing on Master screen")
items = [x.strip() for x in m.group(1).split(",") if x.strip()]
preferred = ["Users", "Trash2", "ReceiptText"]
ordered = preferred + [x for x in items if x not in preferred]
block = "import {\n  " + ",\n  ".join(ordered) + ",\n} from 'lucide-react';"
s = s[:m.start()] + block + s[m.end():]
p.write_text(s)
print("Master icon import normalized")
