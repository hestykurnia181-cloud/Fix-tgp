from pathlib import Path
import re

ROOT = Path("project")

# --- Staff logout + live synchronized service history ---
ctx = ROOT / "src/context/TgpContext.tsx"
if not ctx.exists():
    raise RuntimeError("TgpContext.tsx not found")
s = ctx.read_text()

if "logout: () => void;" not in s:
    # Put logout next to currentSession in the context contract.
    m = re.search(r"(\n\s*currentSession:\s*[^;]+;)", s)
    if not m:
        raise RuntimeError("currentSession contract anchor not found")
    s = s[:m.end()] + "\n  logout: () => void;" + s[m.end():]

if "const logout = () => {" not in s:
    anchor = "  const clearMessages = () => {"
    fn = """  const logout = () => {
    // Remove only authentication/session state; never clear business data or pending sync.
    try {
      Object.keys(localStorage)
        .filter((key) => /session|auth/i.test(key) && !/pending_sync/i.test(key))
        .forEach((key) => localStorage.removeItem(key));
    } catch {}
    setCurrentSession(null);
  };

"""
    if anchor not in s:
        raise RuntimeError("clearMessages anchor not found")
    s = s.replace(anchor, fn + anchor, 1)

if re.search(r"\bactiveSales,\s*\n", s) and "        logout," not in s:
    s = s.replace("        activeSales,\n", "        logout,\n        activeSales,\n", 1)

ctx.write_text(s)

# Make sure the staff module is registered even on builds that predate the staff branch.
types = ROOT / "src/types.ts"
if types.exists():
    t = types.read_text()
    if "'SERVICE_STAFF_MODULE'" not in t:
        t = t.replace("  | 'OPERATIONAL_PERIODS_MODULE'\n", "  | 'OPERATIONAL_PERIODS_MODULE'\n  | 'SERVICE_STAFF_MODULE'\n", 1)
        types.write_text(t)

app = ROOT / "src/App.tsx"
if app.exists():
    t = app.read_text()
    if "ServiceStaffScreen" not in t:
        t = t.replace("import { PosScreen } from './screens/PosScreen';",
                      "import { PosScreen } from './screens/PosScreen';\nimport { ServiceStaffScreen } from './screens/ServiceStaffScreen';", 1)
    if "case 'SERVICE_STAFF_MODULE':" not in t:
        t = t.replace("      case 'POS_MODULE':",
                      "      case 'SERVICE_STAFF_MODULE':\n        return <ServiceStaffScreen />;\n      case 'POS_MODULE':", 1)
    app.write_text(t)

staff = ROOT / "src/screens/ServiceStaffScreen.tsx"
if staff.exists():
    t = staff.read_text()
    # Use the live synchronized sales state from TgpContext instead of a localStorage snapshot.
    t = re.sub(
        r"const \{currentSession,activeBusiness,operationalPeriods\}=useTgp\(\);",
        "const {currentSession,activeBusiness,operationalPeriods,sales,logout}=useTgp();",
        t, count=1
    )
    t = re.sub(
        r"\s*let sales:any\[\]=\[\];try\{sales=JSON\.parse\(localStorage\.getItem\('sales'\)\|\|'\[\]'\)\}catch\{sales=\[\]\}",
        "",
        t, count=1
    )
    # If the current version still uses the older declaration, remove that too.
    t = re.sub(r"\s*let all:any\[\]=\[\];try\{all=JSON\.parse\(localStorage\.getItem\('sales'\)\|\|'\[\]'\)\}catch\{\}",
               "", t, count=1)
    t = t.replace("return all.flatMap((sale:any)=>", "return sales.flatMap((sale:any)=>")
    if "logout" in t and "Keluar" not in t:
        # Insert a visible logout action in the staff header.
        needle = '<h2 className="text-xl font-black">Jasa Saya</h2>'
        replacement = needle + '<button type="button" onClick={logout} className="ml-auto px-3 py-2 rounded-xl bg-slate-900 text-white text-xs font-extrabold">Keluar</button>'
        t = t.replace(needle, replacement, 1)
    staff.write_text(t)

# If the existing staff screen has no synchronized sales dependency because it is an older variant,
# add a compact replacement screen based on the current context API.
if not staff.exists():
    staff.write_text("""import React,{useMemo,useRef,useState} from 'react';
import {Camera,CalendarDays,Scissors,UserRound} from 'lucide-react';
import {useTgp} from '../context/TgpContext';
import {UserRole} from '../types';

type Attendance={id:string;userId:string;businessId:string;dateKey:string;checkInAt?:number;checkInPhoto?:string;checkOutAt?:number;checkOutPhoto?:string};
const KEY='tgp_service_attendance_v1';
const read=():Attendance[]=>{try{return JSON.parse(localStorage.getItem(KEY)||'[]')}catch{return[]}};
const save=(x:Attendance[])=>localStorage.setItem(KEY,JSON.stringify(x));
const day=(d:Date)=>{const x=new Date(d.getTime()-d.getTimezoneOffset()*60000);return x.toISOString().slice(0,10)};
const money=(n:number)=>'Rp '+Math.round(n).toLocaleString('id-ID');

export const ServiceStaffScreen:React.FC=()=>{
 const {currentSession,activeBusiness,sales,logout}=useTgp();
 const user=currentSession?.user, role=user?.role;
 const [rows,setRows]=useState(read); const [mode,setMode]=useState<'IN'|'OUT'|null>(null); const ref=useRef<HTMLInputElement>(null);
 const today=day(new Date()), todayRow=rows.find(x=>x.userId===user?.userId&&x.businessId===activeBusiness?.businessId&&x.dateKey===today);
 const history=useMemo(()=>sales.filter((sale:any)=>sale.businessId===activeBusiness?.businessId).flatMap((sale:any)=> (Array.isArray(sale.items)?sale.items:[]).filter((i:any)=>[user?.userId,user?.username,user?.fullName].filter(Boolean).map(String).includes(String(i.serviceStaffId||i.staffId||i.assignedStaffId))).map((i:any)=>({id:String(sale.saleId||sale.orderId||sale.transactionId)+'-'+String(i.itemId||i.id||i.name),ts:Number(sale.timestamp||sale.createdAt||0),name:i.name||i.itemName||i.serviceName||'Jasa',qty:Number(i.quantity||1),amount:Number(i.subtotal??i.total??i.amount??((i.price||0)*(i.quantity||1)))})).sort((a:any,b:any)=>b.ts-a.ts),[sales,activeBusiness?.businessId,user?.userId,user?.username,user?.fullName]);
 const photo=(e:React.ChangeEvent<HTMLInputElement>)=>{const f=e.target.files?.[0];if(!f||!mode||!user||!activeBusiness)return;const r=new FileReader();r.onload=()=>{const old=read().find(x=>x.userId===user.userId&&x.businessId===activeBusiness.businessId&&x.dateKey===today),row=old||{id:'att-'+user.userId+'-'+today,userId:user.userId,businessId:activeBusiness.businessId,dateKey:today};if(mode==='IN'){row.checkInAt=Date.now();row.checkInPhoto=String(r.result||'')}else{row.checkOutAt=Date.now();row.checkOutPhoto=String(r.result||'')}const n=[...read().filter(x=>x.id!==row.id),row];save(n);setRows(n);setMode(null);e.target.value=''};r.readAsDataURL(f)};
 if(role!==UserRole.STAFF)return <div className="p-6">Akses ditolak.</div>;
 return <div className="space-y-4 pb-24"><input ref={ref} type="file" accept="image/*" capture="user" onChange={photo} className="hidden"/>
 <div className="bg-white rounded-3xl border p-5 flex items-center gap-3"><Scissors className="w-7 h-7 text-emerald-600"/><div><div className="text-[10px] uppercase font-black text-emerald-700">SKY BARBERSHOP • JASA</div><h2 className="text-xl font-black">Jasa Saya</h2></div><button onClick={logout} className="ml-auto px-3 py-2 rounded-xl bg-slate-900 text-white text-xs font-extrabold">Keluar</button></div>
 <div className="bg-white rounded-3xl border p-4"><b>Absensi Foto</b><div className="grid grid-cols-2 gap-3 mt-3"><button disabled={!!todayRow?.checkInAt} onClick={()=>{setMode('IN');ref.current?.click()}} className="p-4 rounded-2xl border bg-emerald-50 disabled:opacity-50">Absen Masuk</button><button disabled={!todayRow?.checkInAt||!!todayRow?.checkOutAt} onClick={()=>{setMode('OUT');ref.current?.click()}} className="p-4 rounded-2xl border bg-blue-50 disabled:opacity-50">Absen Pulang</button></div></div>
 <div className="bg-white rounded-3xl border p-4"><div className="flex items-center gap-2 mb-3"><CalendarDays className="w-4 h-4"/><b>Riwayat Pekerjaan Saya</b></div>{history.length?history.map((x:any)=><div key={x.id} className="p-3 border-b flex justify-between"><div><b>{x.name}</b><div className="text-xs text-slate-500">{new Date(x.ts).toLocaleString('id-ID')} • Qty {x.qty}</div></div><b>{money(x.amount)}</b></div>):<div className="p-6 text-center text-slate-400"><UserRound className="mx-auto mb-2"/>Belum ada riwayat jasa.</div>}</div>
 </div>;
};
""")

print("staff-sync-logout patch prepared")
