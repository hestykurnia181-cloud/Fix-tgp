from pathlib import Path
ROOT=Path('project')

def rep(path,old,new,label):
 s=path.read_text()
 if old not in s: raise RuntimeError(label)
 path.write_text(s.replace(old,new,1))

pos=ROOT/'src/screens/PosScreen.tsx'
rep(pos,'''  const serviceProviders = allStaffForActiveBusiness.filter((user) =>
    [UserRole.STAFF, UserRole.MANAGER, UserRole.KASIR].includes(user.role)
  );''','''  const serviceProviders = allStaffForActiveBusiness.filter((user) => normalizeUserRole(user.role) === UserRole.STAFF).sort((a,b)=>String(a.fullName||'').localeCompare(String(b.fullName||''),'id'));''','Sky POS staff list anchor not found')

ctx=ROOT/'src/context/TgpContext.tsx'
rep(ctx,'''      subtotal: ci.quantity * (ci.unitPrice ?? getItemUnitPrice(ci.item)),
      ...(ci.item.type === 'SERVICE' && ci.serviceStaffId ? {''','''      subtotal: ci.quantity * (ci.unitPrice ?? getItemUnitPrice(ci.item)),
      itemType: ci.item.type,
      ...(ci.item.type === 'SERVICE' && ci.serviceStaffId ? {''','Completed service item anchor not found')
rep(ctx,"        const staff = users.find((u) => u.userId === serviceStaffId);","        const staff = users.find((u) => u.userId === serviceStaffId && normalizeUserRole(u.role) === UserRole.STAFF && (u.businessId === effectiveBusinessId || (u.assignedBusinessIds || []).includes(effectiveBusinessId)));","Checkout staff fallback anchor not found")

types=ROOT/'src/types.ts'
s=types.read_text()
if "itemType?: ItemEntity['type'];" not in s:
 s=s.replace('  subtotal: number;','  subtotal: number;\n  itemType?: ItemEntity[\'type\'];',1)
 types.write_text(s)

staff=ROOT/'src/screens/ServiceStaffScreen.tsx'
s=staff.read_text()
rep(staff,'const {currentSession,activeBusiness,operationalPeriods,sales,logout}=useTgp();','const {currentSession,activeBusiness,operationalPeriods,sales,users,logout}=useTgp();','Staff users context anchor not found')
old='''   const matches=(value:any)=>{
     const ids=[user.userId,user.username,user.fullName].filter(Boolean).map(String);
     return ids.includes(String(value??''));
   };'''
new='''   const normalizeIdentity=(value:any)=>String(value??'').normalize('NFKD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'');
   const identityKeys=new Set([user.userId,user.username,user.fullName,...users.filter((u:any)=>u.role===UserRole.STAFF&&String(u.businessId||'')===String(activeBusiness.businessId)).flatMap((u:any)=>[u.userId,u.username,u.fullName])].filter(Boolean).map(normalizeIdentity));
   const matches=(value:any)=>identityKeys.has(normalizeIdentity(value));'''
rep(staff,old,new,'Staff identity matcher anchor not found')
old='''     if(selectedPeriod){
       const key=selectedPeriod.periodKey;
       const salePeriod=String(sale.periodId||'');
       const month=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0');
       if(salePeriod && salePeriod!==selectedPeriod.periodId)return[];
       if(!salePeriod && month!==key)return[];
     }'''
new='''     if(selectedPeriod && range!=='ALL'){
       const start=Number(selectedPeriod.startDate||0);
       const end=Number(selectedPeriod.endDate||0);
       if(start && end && (ts<start || ts>end))return[];
     }'''
rep(staff,old,new,'Staff period filter anchor not found')
old='''       const assigned =
         matches(item.serviceStaffId)||matches(item.staffId)||matches(item.assignedStaffId)||matches(item.serviceStaffName)||matches(item.assignedStaffName)||
         matches(item.serviceStaff?.userId)||matches(item.serviceStaff?.username)||matches(item.serviceStaff?.fullName)||
         matches(item.staff?.userId)||matches(item.staff?.username)||matches(item.staff?.fullName)||
         matches(sale.serviceStaffId)||matches(sale.staffId)||matches(sale.assignedStaffId)||matches(sale.serviceStaffName)||matches(sale.assignedStaffName);
       if(!assigned)return[];'''
new='''       const itemAssigned=matches(item.serviceStaffId)||matches(item.staffId)||matches(item.assignedStaffId)||matches(item.serviceStaffName)||matches(item.assignedStaffName)||matches(item.serviceStaff?.userId)||matches(item.serviceStaff?.username)||matches(item.serviceStaff?.fullName)||matches(item.staff?.userId)||matches(item.staff?.username)||matches(item.staff?.fullName);
       const saleAssigned=matches(sale.serviceStaffId)||matches(sale.staffId)||matches(sale.assignedStaffId)||matches(sale.serviceStaffName)||matches(sale.assignedStaffName);
       if(!itemAssigned&&!saleAssigned)return[];'''
rep(staff,old,new,'Staff assignment matcher anchor not found')
staff.write_text(s)
print('SKY BARBERSHOP STAFF FIX APPLIED')