from pathlib import Path
import re

ROOT = Path("project")

# 1) Persist the item type in completed POS sales so a staff assignment can
#    unambiguously mean "this SERVICE item was performed by this staff".
types = ROOT / "src/types.ts"
t = types.read_text()
if "  itemType?: 'PRODUCT' | 'SERVICE' | 'RAW_MATERIAL' | 'MENU_DISH' | 'FINISHED_GOODS';" not in t:
    anchor = "  subtotal: number;\n"
    if anchor not in t:
        raise RuntimeError("SaleOrderItem subtotal anchor not found")
    t = t.replace(anchor, anchor + "  itemType?: 'PRODUCT' | 'SERVICE' | 'RAW_MATERIAL' | 'MENU_DISH' | 'FINISHED_GOODS';\n", 1)
    types.write_text(t)

# 2) Put itemType into every completed sale item.
ctx = ROOT / "src/context/TgpContext.tsx"
s = ctx.read_text()
old = """      subtotal: ci.quantity * (ci.unitPrice ?? getItemUnitPrice(ci.item)),
      ...(ci.item.type === 'SERVICE' && ci.serviceStaffId ? {"""
new = """      subtotal: ci.quantity * (ci.unitPrice ?? getItemUnitPrice(ci.item)),
      itemType: ci.item.type,
      ...(ci.item.type === 'SERVICE' && ci.serviceStaffId ? {"""
if old in s and "      itemType: ci.item.type," not in s:
    s = s.replace(old, new, 1)
ctx.write_text(s)

# 3) Make staff history matching robust and period-independent when "Semua" is selected.
staff = ROOT / "src/screens/ServiceStaffScreen.tsx"
x = staff.read_text()

old_matches = """   const matches=(value:any)=>{
     const ids=[user.userId,user.username,user.fullName].filter(Boolean).map(String);
     return ids.includes(String(value??''));
   };"""
new_matches = """   const normalizeIdentity=(value:any)=>String(value??'').trim().toLowerCase();
   const identityKeys=new Set([user.userId,user.username,user.fullName].filter(Boolean).map(normalizeIdentity));
   const matches=(value:any)=>identityKeys.has(normalizeIdentity(value));"""
if old_matches in x:
    x = x.replace(old_matches, new_matches, 1)

old_period = """     if(selectedPeriod){
       const key=selectedPeriod.periodKey;
       const salePeriod=String(sale.periodId||'');
       const month=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0');
       if(salePeriod && salePeriod!==selectedPeriod.periodId)return[];
       if(!salePeriod && month!==key)return[];
     }"""
new_period = """     if(selectedPeriod && range!=='ALL'){
       const key=selectedPeriod.periodKey;
       const salePeriod=String(sale.periodId||'');
       const month=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0');
       if(salePeriod && salePeriod!==selectedPeriod.periodId)return[];
       if(!salePeriod && month!==key)return[];
     }"""
if old_period in x:
    x = x.replace(old_period, new_period, 1)

old_assigned = """       const assigned =
         matches(item.serviceStaffId)||matches(item.staffId)||matches(item.assignedStaffId)||matches(item.serviceStaffName)||matches(item.assignedStaffName)||
         matches(item.serviceStaff?.userId)||matches(item.serviceStaff?.username)||matches(item.serviceStaff?.fullName)||
         matches(item.staff?.userId)||matches(item.staff?.username)||matches(item.staff?.fullName)||
         matches(sale.serviceStaffId)||matches(sale.staffId)||matches(sale.assignedStaffId)||matches(sale.serviceStaffName)||matches(sale.assignedStaffName);
       if(!assigned)return[];"""
new_assigned = """       const itemIsService = item.itemType === 'SERVICE' || item.type === 'SERVICE';
       const itemAssigned =
         matches(item.serviceStaffId)||matches(item.staffId)||matches(item.assignedStaffId)||matches(item.serviceStaffName)||matches(item.assignedStaffName)||
         matches(item.serviceStaff?.userId)||matches(item.serviceStaff?.username)||matches(item.serviceStaff?.fullName)||
         matches(item.staff?.userId)||matches(item.staff?.username)||matches(item.staff?.fullName);
       const saleAssigned =
         matches(sale.serviceStaffId)||matches(sale.staffId)||matches(sale.assignedStaffId)||matches(sale.serviceStaffName)||matches(sale.assignedStaffName);
       // New sales carry itemType. Legacy sales may only carry the staff at sale level;
       // for a SERVICE business we preserve those historical staff assignments.
       const assigned = itemAssigned || (saleAssigned && (itemIsService || activeBusiness.templateType === 'SERVICE'));
       if(!assigned)return[];"""
if old_assigned in x:
    x = x.replace(old_assigned, new_assigned, 1)

# Also include itemType in the memo dependency only if the source uses no dynamic dependency.
staff.write_text(x)

print("Service staff history hardening applied")
