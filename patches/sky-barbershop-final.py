from pathlib import Path
ROOT=Path('project')
def rep(path,old,new,label):
 s=path.read_text()
 if old not in s: raise RuntimeError(label)
 path.write_text(s.replace(old,new,1))
pos=ROOT/'src/screens/PosScreen.tsx'
rep(pos,'''  const serviceProviders = allStaffForActiveBusiness.filter((user) =>
    [UserRole.STAFF, UserRole.MANAGER, UserRole.KASIR].includes(user.role)
  );''','''  const serviceProviders = allStaffForActiveBusiness.filter((user) => user.role === UserRole.STAFF).sort((a,b)=>String(a.fullName||'').localeCompare(String(b.fullName||''),'id'));''','Sky POS staff list anchor not found')
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
print('SKY BARBERSHOP POS FIX APPLIED')