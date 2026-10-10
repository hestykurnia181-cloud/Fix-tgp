from pathlib import Path
import re
root = Path("project/src")
terms = re.compile(r"attendance|absen|absensi|check.?in|check.?out|kehadiran", re.I)
print("=== ATTENDANCE SOURCE DISCOVERY ===")
for p in sorted(root.rglob("*")):
    if not p.is_file() or p.suffix not in {".ts",".tsx",".js",".jsx",".sql"}:
        continue
    try: s=p.read_text(errors="ignore")
    except Exception: continue
    hits=[(i,line.strip()) for i,line in enumerate(s.splitlines(),1) if terms.search(line)]
    if hits:
        print(f"\nFILE {p} ({len(hits)} hits)")
        for i,line in hits[:35]:
            print(f"{i}: {line[:220]}")
