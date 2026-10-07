from pathlib import Path
ROOT=Path("project")

def replace_once(path, old, new, label):
    s=path.read_text()
    if old not in s:
        raise RuntimeError(label+" anchor not found")
    path.write_text(s.replace(old,new,1))

pos=ROOT/"src/screens/PosScreen.tsx"
replace_once(pos,
"""  const serviceProviders = allStaffForActiveBusiness.filter((user) =>
    [UserRole.STAFF, UserRole.MANAGER, UserRole.KASIR].includes(user.role)
  );""",
"""  const serviceProviders = allStaffForActiveBusiness
    .filter((user) => normalizeUserRole(user.role) === UserRole.STAFF)
    .sort((a,b)=>String(a.fullName||'').localeCompare(String(b.fullName||''),'id'));""",
"Sky POS staff list")
replace_once(pos,
"""      ![UserRole.MASTER, UserRole.OWNER, UserRole.ADMIN_OWNER, UserRole.ADMIN_DIVISI, UserRole.WAREHOUSE].includes(normalizeUserRole(u.role))
    );""",
"""      normalizeUserRole(u.role) === UserRole.STAFF
    );""",
"Sky POS staff validation")

ctx=ROOT/"src/context/TgpContext.tsx"
replace_once(ctx,
"""      subtotal: ci.quantity * (ci.unitPrice ?? getItemUnitPrice(ci.item)),
      ...(ci.item.type === 'SERVICE' && ci.serviceStaffId ? {""",
"""      subtotal: ci.quantity * (ci.unitPrice ?? getItemUnitPrice(ci.item)),
      itemType: ci.item.type,
      ...(ci.item.type === 'SERVICE' && ci.serviceStaffId ? {""",
"completed service item type")
replace_once(ctx,
"""        const staff = users.find((u) => u.userId === serviceStaffId);""",
"""        const staff = users.find((u) =>
          u.userId === serviceStaffId &&
          normalizeUserRole(u.role) === UserRole.STAFF &&
          (u.businessId === effectiveBusinessId || (u.assignedBusinessIds || []).includes(effectiveBusinessId))
        );""",
"checkout staff fallback")

types=ROOT/"src/types.ts"
s=types.read_text()
if "itemType?: ItemEntity['type'];" not in s:
    replace_once(types,"  subtotal: number;\n  serviceStaffId?: string;","  subtotal: number;\n  itemType?: ItemEntity['type'];\n  serviceStaffId?: string;","SaleOrderItem type")

staff=ROOT/"src/screens/ServiceStaffScreen.tsx"
s=staff.read_text()
replace_once(staff,
"const {currentSession,activeBusiness,operationalPeriods,sales,logout}=useTgp();",
"const {currentSession,activeBusiness,operationalPeriods,sales,users,logout}=useTgp();",
"staff users context")
start=s.find(" const history=useMemo(()=>{")
end=s.find("\n const total=history.reduce",start)
if start<0 or end<0:
    raise RuntimeError("staff history block not found")
history=""" const history=useMemo(()=>{
   if(!user||!activeBusiness)return[];
   const norm=(v:any)=>String(v??'').normalize('NFKD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'');
   const base=[user.userId,user.username,user.fullName].filter(Boolean).map(norm);
   const canonical=users.filter((u:any)=>
     norm(u.role)===norm(UserRole.STAFF) &&
     base.some((k)=>k===norm(u.userId)||k===norm(u.username)||k===norm(u.fullName)) &&
     (String(u.businessId||'')===String(activeBusiness.businessId)||(u.assignedBusinessIds||[]).map(String).includes(String(activeBusiness.businessId)))
   );
   const keys=new Set([...base,...canonical.flatMap((u:any)=>[u.userId,u.username,u.fullName]).map(norm)].filter(Boolean));
   const matches=(v:any)=>keys.has(norm(v));
   const now=new Date(),ws=weekStart(now),ms=monthStart(now);
   const selectedStart=selectedPeriod?.startDate?Number(selectedPeriod.startDate):undefined;
   const selectedEnd=selectedPeriod?.endDate?Number(selectedPeriod.endDate):undefined;
   return sales.flatMap((sale:any)=>{
     if(String(sale.businessId||'')!==String(activeBusiness.businessId))return[];
     const ts=Number(sale.timestamp||sale.createdAt||sale.date||0);if(!ts)return[];
     const d=new Date(ts);
     if(range==='DAY'&&dateKey(d)!==today)return[];
     if(range==='WEEK'&&ts<ws)return[];
     if(range==='MONTH'&&ts<ms)return[];
     if(periodId!=='CURRENT'&&selectedStart!==undefined&&selectedEnd!==undefined&&(ts<selectedStart||ts>selectedEnd))return[];
     const items=Array.isArray(sale.items)?sale.items:[];
     return items.flatMap((item:any)=>{
       const isService=item.itemType==='SERVICE'||item.type==='SERVICE'||!!item.serviceStaffId||!!item.serviceStaffName;
       if(!isService)return[];
       const itemAssigned=matches(item.serviceStaffId)||matches(item.staffId)||matches(item.assignedStaffId)||matches(item.serviceStaffName)||matches(item.assignedStaffName)||matches(item.serviceStaff?.userId)||matches(item.serviceStaff?.username)||matches(item.serviceStaff?.fullName)||matches(item.staff?.userId)||matches(item.staff?.username)||matches(item.staff?.fullName);
       const saleAssigned=matches(sale.serviceStaffId)||matches(sale.staffId)||matches(sale.assignedStaffId)||matches(sale.serviceStaffName)||matches(sale.assignedStaffName);
       if(!itemAssigned&&!saleAssigned)return[];
       const qty=Number(item.quantity||item.qty||1);
       const amount=Number(item.subtotal??item.total??item.amount??item.totalAmount??((item.price||item.unitPrice||0)*qty));
       const commission=Number(item.serviceCommissionAmount??item.commissionAmount??item.commission??0);
       const name=item.name||item.itemName||item.serviceName||item.productName||'Jasa';
       return [{id:String(sale.saleId||sale.orderId||sale.transactionId||ts)+'-'+String(item.itemId||item.id||name),ts,name,qty,amount,commission,staffName:item.serviceStaffName||sale.serviceStaffName||user.fullName}];
     });
   }).sort((a:any,b:any)=>b.ts-a.ts);
 }"""
s=s[:start]+history+s[end:]
s=s.replace(
" },[sales,user?.userId,user?.username,user?.fullName,activeBusiness?.businessId,selectedPeriod?.periodId,selectedPeriod?.periodKey,range,today]);",
" },[sales,users,user?.userId,user?.username,user?.fullName,activeBusiness?.businessId,periodId,selectedPeriod?.startDate,selectedPeriod?.endDate,range,today]);",
1)
s=s.replace(
'<b className="text-sm">{x.name}</b><div className="text-[10px] text-slate-500">',
'<b className="text-sm">{x.name}</b><div className="text-[10px] text-emerald-700 font-semibold">Petugas: {x.staffName}</div><div className="text-[10px] text-slate-500">',
1)
staff.write_text(s)
print("Sky Barbershop staff fix prepared")
