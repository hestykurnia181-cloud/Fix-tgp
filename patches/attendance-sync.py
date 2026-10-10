from pathlib import Path
p=Path("project/src/screens/ServiceStaffScreen.tsx")
s=p.read_text()
def replace(old,new,label):
 global s
 if new in s:
  print("[attendance] already applied:",label); return
 if old not in s:
  raise RuntimeError("[attendance] anchor missing: "+label)
 s=s.replace(old,new,1)
replace(
 "const {currentSession,activeBusiness,operationalPeriods,sales,users,logout}=useTgp();",
 "const {currentSession,activeBusiness,operationalPeriods,sales,users,logout,allAttendances,recordAttendance}=useTgp();",
 "use shared attendance context"
)
replace(
 "const todayAttendance=attendance.find(a=>a.userId===user?.userId&&a.businessId===activeBusiness?.businessId&&a.dateKey===today);",
 """const localTodayAttendance=attendance.find(a=>a.userId===user?.userId&&a.businessId===activeBusiness?.businessId&&a.dateKey===today);
  const remoteTodayAttendances=allAttendances.filter(a=>a.userId===user?.userId&&a.businessId===activeBusiness?.businessId&&dateKey(new Date(a.timestamp))===today);
  const remoteCheckIn=remoteTodayAttendances.find(a=>a.type==='MASUK');
  const remoteCheckOut=remoteTodayAttendances.find(a=>a.type==='PULANG');
  const todayAttendance:Attendance|undefined=localTodayAttendance
    ? {...localTodayAttendance,checkInAt:localTodayAttendance.checkInAt||remoteCheckIn?.timestamp,checkOutAt:localTodayAttendance.checkOutAt||remoteCheckOut?.timestamp}
    : (remoteCheckIn||remoteCheckOut ? {id:'att-'+user?.userId+'-'+today,userId:user?.userId||'',businessId:activeBusiness?.businessId||'',dateKey:today,checkInAt:remoteCheckIn?.timestamp,checkOutAt:remoteCheckOut?.timestamp} : undefined);""",
 "derive button state from server attendance"
)
replace(
 "const next=[...readAttendance().filter(a=>a.id!==row.id),row];saveAttendance(next);setAttendance(next);setTarget(null);e.target.value='';",
 """const next=[...readAttendance().filter(a=>a.id!==row.id),row];try{saveAttendance(next)}catch(storageError){console.warn('[attendance] photo cache unavailable; syncing attendance timestamp anyway',storageError)}setAttendance(next);
      // Persist attendance to the shared Supabase-backed attendance stream so Owner/Admin Owner reports see it on every device.
      recordAttendance(target==='IN'?'MASUK':'PULANG',target==='IN'?'Absensi masuk (foto diambil)':'Absensi pulang (foto diambil)');
      setTarget(null);e.target.value='';""",
 "persist photo attendance to shared database"
)
s=s.replace("  },[sales,user?.userId", "  },[sales,user?.userId") if False else s
p.write_text(s)

# Make Owner/Admin Owner attendance reports include employees who have not checked in yet.
report=Path("project/src/screens/EmployeeManagementScreen.tsx")
rs=report.read_text()
old="    return Array.from(byUser.entries()).map(([userId, row]) => ({ userId, ...row, days: row.dates.size, incomplete: Math.max(0, row.masuk - row.pulang) }));"
new="""    for (const employee of employees) {
      if (!byUser.has(employee.userId)) {
        byUser.set(employee.userId, { name: employee.fullName || employee.username || 'Karyawan', dates: new Set<string>(), masuk: 0, pulang: 0, incomplete: 0 });
      }
    }
    return Array.from(byUser.entries()).map(([userId, row]) => ({ userId, ...row, days: row.dates.size, incomplete: Math.max(0, row.masuk - row.pulang) }));"""
if new not in rs:
 if old not in rs: raise RuntimeError("[attendance] report summary anchor missing")
 rs=rs.replace(old,new,1)
if "}, [businessAttendance, employees]);" not in rs:
 if "}, [businessAttendance]);" not in rs: raise RuntimeError("[attendance] report memo dependency anchor missing")
 rs=rs.replace("}, [businessAttendance]);","}, [businessAttendance, employees]);",1)
old_label="{row.incomplete ? `${row.incomplete} belum pulang` : 'Lengkap'}"
new_label="{row.masuk === 0 ? 'Belum absen' : row.incomplete ? `${row.incomplete} belum pulang` : 'Lengkap'}"
if new_label not in rs:
 if old_label not in rs: raise RuntimeError("[attendance] report status label anchor missing")
 rs=rs.replace(old_label,new_label,1)
report.write_text(rs)
print("[attendance] staff check-in/out sync and absent-staff report rows applied")
