from pathlib import Path

ROOT = Path("project")

def rep(path, old, new, label):
    s = path.read_text()
    if old not in s:
        raise RuntimeError(label)
    path.write_text(s.replace(old, new, 1))

# Keep the existing Sky Barbershop assignment/sync hardening from this patch.
staff = ROOT / "src/screens/ServiceStaffScreen.tsx"
s = staff.read_text()
old = """   const identityKeys=new Set([user.userId,user.username,user.fullName,...users.filter((u:any)=>u.role===UserRole.STAFF&&String(u.businessId||'')===String(activeBusiness.businessId)).flatMap((u:any)=>[u.userId,u.username,u.fullName])].filter(Boolean).map(normalizeIdentity));
   const matches=(value:any)=>identityKeys.has(normalizeIdentity(value));"""
new = """   const freshUser=users.find((u:any)=>String(u.userId)===String(user.userId))||user;
   const identityKeys=new Set([freshUser.userId,freshUser.username,freshUser.fullName].filter(Boolean).map(normalizeIdentity));
   const matches=(value:any)=>identityKeys.has(normalizeIdentity(value));"""
rep(staff, old, new, "Staff identity isolation anchor not found")
old = """     const items=Array.isArray(sale.items)?sale.items:[];
     return items.flatMap((item:any)=>{
       const itemAssigned=matches(item.serviceStaffId)||matches(item.staffId)||matches(item.assignedStaffId)||matches(item.serviceStaffName)||matches(item.assignedStaffName)||matches(item.serviceStaff?.userId)||matches(item.serviceStaff?.username)||matches(item.serviceStaff?.fullName)||matches(item.staff?.userId)||matches(item.staff?.username)||matches(item.staff?.fullName);"""
new = """     const items=Array.isArray(sale.items)?sale.items:[];
     return items.flatMap((item:any)=>{
       const isService=item.itemType==='SERVICE'||item.type==='SERVICE'||Boolean(item.serviceStaffId||item.serviceStaffName||item.serviceCommissionAmount||item.serviceOwnerShareAmount);
       if(!isService)return[];
       const itemAssigned=matches(item.serviceStaffId)||matches(item.staffId)||matches(item.assignedStaffId)||matches(item.serviceStaffName)||matches(item.assignedStaffName)||matches(item.serviceStaff?.userId)||matches(item.serviceStaff?.username)||matches(item.serviceStaff?.fullName)||matches(item.staff?.userId)||matches(item.staff?.username)||matches(item.staff?.fullName);"""
rep(staff, old, new, "Staff service item filter anchor not found")

ctx = ROOT / "src/context/TgpContext.tsx"
rep(ctx,
"""      u.userId === serviceStaffId &&
      (u.businessId === activeBusinessId || (u.assignedBusinessIds || []).includes(activeBusinessId)) &&
      ![UserRole.MASTER, UserRole.OWNER, UserRole.ADMIN_OWNER, UserRole.ADMIN_DIVISI, UserRole.WAREHOUSE].includes(normalizeUserRole(u.role))""",
"""      u.userId === serviceStaffId &&
      (u.businessId === activeBusinessId || (u.assignedBusinessIds || []).includes(activeBusinessId)) &&
      normalizeUserRole(u.role) === UserRole.STAFF""",
"Service assignment role validation anchor not found")
rep(ctx,
"""    if (activeBiz?.templateType === BusinessTemplate.SERVICE) {
      // Backward compatibility: bila hanya ada satu jasa yang dibuat sebelum fitur per-item, gunakan pilihan checkout sebagai fallback.""",
"""    if (activeBiz?.templateType === BusinessTemplate.SERVICE) {
      const unassignedService = serviceCartEntries.find((ci) => !ci.serviceStaffId);
      if (unassignedService) {
        setErrorMessage('Pilih Staff untuk jasa "' + unassignedService.item.name + '" sebelum menyelesaikan transaksi.');
        return null;
      }
      const invalidServiceAssignment = serviceCartEntries.find((ci) => {
        const staff = users.find((u) =>
          u.userId === ci.serviceStaffId &&
          normalizeUserRole(u.role) === UserRole.STAFF &&
          (u.businessId === effectiveBusinessId || (u.assignedBusinessIds || []).includes(effectiveBusinessId))
        );
        return !staff;
      });
      if (invalidServiceAssignment) {
        setErrorMessage('Staff jasa tidak valid atau tidak terdaftar pada bisnis aktif.');
        return null;
      }
      // Legacy checkout parameter is retained only for compatibility.""",
"Service checkout validation anchor not found")
rep(ctx,
"""      // Petugas jasa bersifat opsional. Jika tidak dipilih, tidak ada komisi
      // yang dipotong dan seluruh nilai jasa menjadi bagian bisnis.
      const totalServiceCommission = detailedItems.reduce((sum, item) => sum + (item.serviceCommissionAmount || 0), 0);""",
"""      const totalServiceCommission = detailedItems.reduce((sum, item) => sum + (item.serviceCommissionAmount || 0), 0);""",
"Optional service commission block not found")

pos = ROOT / "src/screens/PosScreen.tsx"
rep(pos,
"""  const serviceProviders = allStaffForActiveBusiness.filter((user) =>
    [UserRole.STAFF, UserRole.MANAGER, UserRole.KASIR].includes(user.role)
  );""",
"""  const serviceProviders = allStaffForActiveBusiness
    .filter((user) => user.role === UserRole.STAFF)
    .sort((a, b) => String(a.fullName || '').localeCompare(String(b.fullName || ''), 'id'));""",
"POS staff provider anchor not found")
rep(pos, "Petugas jasa opsional; transaksi tetap bisa diselesaikan tanpa memilih staff.", "Petugas jasa wajib dipilih sebelum transaksi diselesaikan.", "POS optional text not found")
rep(pos, "Opsional</span>", "Wajib</span>", "POS optional badge not found")
rep(pos, '<option value="">Tanpa petugas</option>', '<option value="">Pilih Staff</option>', "POS no staff option not found")

sync = ROOT / "src/services/supabaseSyncService.ts"
q = sync.read_text()
start = q.find("  private async rawUpsertRecord(table: string, dbPayload: any) {")
end = q.find("  private readPendingSync", start)
if start < 0 or end < 0:
    raise RuntimeError("rawUpsertRecord block not found")
raw = """  private async rawUpsertRecord(table: string, dbPayload: any) {
    const supabase = getSupabaseClient();
    if (!supabase) throw new Error('Supabase client is not configured');
    const { error } = await supabase.from(table).upsert(dbPayload);
    if (error) {
      console.warn('[SupabaseSync] Error upserting to ' + table + ':', error.message);
      throw error;
    }
    if (this.channel) {
      this.channel.send({
        type: 'broadcast',
        event: 'tgp_mutation',
        payload: { type: 'INSERT_OR_UPDATE', table, data: dbPayload },
      });
    }
  }

"""
q = q[:start] + raw + q[end:]
for old, new in [
("if (data.length > 0) this.handlers.onSalesUpdated(data.map(mapSaleFromDb));", "this.handlers.onSalesUpdated(data.map(mapSaleFromDb));"),
("if (data.length > 0) this.handlers.onUsersUpdated(data.map(mapUserFromDb));", "this.handlers.onUsersUpdated(data.map(mapUserFromDb));"),
("if (data.length > 0) this.handlers.onItemsUpdated(data.map(mapItemFromDb));", "this.handlers.onItemsUpdated(data.map(mapItemFromDb));"),
("if (data.length > 0) this.handlers.onOperationalPeriodsUpdated(data.map(mapOperationalPeriodFromDb));", "this.handlers.onOperationalPeriodsUpdated(data.map(mapOperationalPeriodFromDb));"),
("if (data.length > 0) this.handlers.onLedgersUpdated(data.map(mapLedgerFromDb));", "this.handlers.onLedgersUpdated(data.map(mapLedgerFromDb));"),
]:
    q = q.replace(old, new)
sync.write_text(q)

# Deployment environment is authoritative when present. This prevents an old
# browser localStorage Supabase project from hijacking the live web app.
sup = ROOT / "src/lib/supabase.ts"
ss = sup.read_text()
old_cfg = """  if (typeof window !== 'undefined') {
    const localUrl = localStorage.getItem('tgp_supabase_url');
    const localKey = localStorage.getItem('tgp_supabase_anon_key');
    if (localUrl && localKey && localUrl.trim().length > 0 && localKey.trim().length > 0) {
      return { url: localUrl.trim(), anonKey: localKey.trim(), source: 'LOCAL' };
    }
  }

  if (envUrl && envKey && envUrl.trim().length > 0 && envKey.trim().length > 0) {
    return { url: envUrl.trim(), anonKey: envKey.trim(), source: 'ENV' };
  }"""
new_cfg = """  // A deployed build must use its configured production Supabase.
  // Browser localStorage may contain an old project from a previous setup;
  // never let that silently override the deployment environment.
  if (envUrl && envKey && envUrl.trim().length > 0 && envKey.trim().length > 0) {
    return { url: envUrl.trim(), anonKey: envKey.trim(), source: 'ENV' };
  }

  if (typeof window !== 'undefined') {
    const localUrl = localStorage.getItem('tgp_supabase_url');
    const localKey = localStorage.getItem('tgp_supabase_anon_key');
    if (localUrl && localKey && localUrl.trim().length > 0 && localKey.trim().length > 0) {
      return { url: localUrl.trim(), anonKey: localKey.trim(), source: 'LOCAL' };
    }
  }"""
if old_cfg not in ss:
    raise RuntimeError("Supabase config priority anchor not found")
sup.write_text(ss.replace(old_cfg, new_cfg, 1))

print("Sky Barbershop assignment + production Supabase config priority patch applied")
