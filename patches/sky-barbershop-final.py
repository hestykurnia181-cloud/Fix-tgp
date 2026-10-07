from pathlib import Path
import re
ROOT=Path('project')

pos=ROOT/'src/screens/PosScreen.tsx'
s=pos.read_text()
s,n=re.subn(r"const serviceProviders = allStaffForActiveBusiness\.filter\(\(user\) =>[\s\S]*?\);", "const serviceProviders = allStaffForActiveBusiness.filter((user) => normalizeUserRole(user.role) === UserRole.STAFF).sort((a,b)=>String(a.fullName||'').localeCompare(String(b.fullName||''),'id'));", s, count=1)
if n!=1: raise RuntimeError('Sky POS provider list not found')
pos.write_text(s)

ctx=ROOT/'src/context/TgpContext.tsx'
s=ctx.read_text()
old="      subtotal: ci.quantity * (ci.unitPrice ?? getItemUnitPrice(ci.item)),\n      ...(ci.item.type === 'SERVICE' && ci.serviceStaffId ? {"
new="      subtotal: ci.quantity * (ci.unitPrice ?? getItemUnitPrice(ci.item)),\n      itemType: ci.item.type,\n      ...(ci.item.type === 'SERVICE' && ci.serviceStaffId ? {"
if old not in s: raise RuntimeError('Completed service item type anchor not found')
s=s.replace(old,new,1)
s,n=re.subn(r"const staff = users\.find\(\(u\) => u\.userId === serviceStaffId\);", "const staff = users.find((u) => u.userId === serviceStaffId && normalizeUserRole(u.role) === UserRole.STAFF && (u.businessId === effectiveBusinessId || (u.assignedBusinessIds || []).includes(effectiveBusinessId)));", s, count=1)
if n!=1: raise RuntimeError('Checkout staff fallback not found')
ctx.write_text(s)

types=ROOT/'src/types.ts'
s=types.read_text()
if "itemType?: ItemEntity['type'];" not in s:
  s=s.replace("  subtotal: number;", "  subtotal: number;\n  itemType?: ItemEntity['type'];", 1)
  types.write_text(s)

staff=ROOT/'src/screens/ServiceStaffScreen.tsx'
s=staff.read_text()
s=s.replace('const {currentSession,activeBusiness,operationalPeriods,sales,logout}=useTgp();','const {currentSession,activeBusiness,operationalPeriods,sales,users,logout}=useTgp();',1)
m=re.search(r'const\\s+history\\s*=\\s*useMemo\\(\\(\\)=>\\{',s)
endm=re.search(r'\\n\\s*const total=history\\.reduce',s[m.end():] if m else '',re.S)
if not m or not endm: raise RuntimeError('Staff history block not found')
start=m.start(); end=m.end()+m.start()+len(s[m.end():])-len(s[m.end():])
end=m.end()+endm.end()
s=s[:start]+block+s[end:]
s=s[:start]+block+s[end:]
s=s.replace(' },[sales,user?.userId,user?.username,user?.fullName,activeBusiness?.businessId,selectedPeriod?.periodId,selectedPeriod?.periodKey,range,today]);',' },[sales,users,user?.userId,user?.username,user?.fullName,activeBusiness?.businessId,periodId,selectedPeriod?.startDate,selectedPeriod?.endDate,range,today]);',1)
s=s.replace('<b className="text-sm">{x.name}</b><div className="text-[10px] text-slate-500">','<b className="text-sm">{x.name}</b><div className="text-[10px] text-emerald-700 font-semibold">Petugas: {x.staffName}</div><div className="text-[10px] text-slate-500">',1)
staff.write_text(s)
print('SKY BARBERSHOP FINAL PATCH APPLIED')