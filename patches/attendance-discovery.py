from pathlib import Path
import re
root=Path("project/src")
def show(path, patterns, radius=16):
 p=root/path
 s=p.read_text(errors="ignore").splitlines()
 print("\\n===== "+path+" =====")
 shown=set()
 for i,line in enumerate(s):
  if any(re.search(pat,line,re.I) for pat in patterns):
   lo=max(0,i-radius); hi=min(len(s),i+radius+1)
   if any(x in shown for x in range(lo,hi)): continue
   shown.update(range(lo,hi))
   print(f"--- lines {lo+1}-{hi} ---")
   for j in range(lo,hi): print(f"{j+1}: {s[j]}")
show("screens/ServiceStaffScreen.tsx", [r"."])
show("screens/AttendanceScreen.tsx", [r"."])
show("context/TgpContext.tsx", [r"recordAttendance",r"allAttendances",r"activeAttendances"], 22)
show("types.ts", [r"interface AttendanceEntity"], 14)
show("screens/EmployeeManagementScreen.tsx", [r"businessAttendance",r"attendanceSummary"], 16)
