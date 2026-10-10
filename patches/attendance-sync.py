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
print("[attendance] staff check-in/out now writes shared attendance records")
