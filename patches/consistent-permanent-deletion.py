from pathlib import Path
root=Path('project')
def rep(path,old,new,label):
 p=root/path;s=p.read_text(encoding='utf-8')
 if new in s:return
 if old not in s:raise RuntimeError('anchor missing: '+label)
 p.write_text(s.replace(old,new,1),encoding='utf-8')
rep('src/context/TgpContext.tsx','  deleteItem: (itemId: string) => boolean;','  deleteItem: (itemId: string) => Promise<boolean>;','item contract')
rep('src/context/TgpContext.tsx','  deleteOutlet: (outletId: string) => boolean;','  deleteOutlet: (outletId: string) => Promise<boolean>;','outlet contract')
p=root/'src/context/TgpContext.tsx';s=p.read_text(encoding='utf-8')
a=s.index('  const deleteItem = (itemId: string): boolean => {');b=s.index('\n  const resetToFactoryData = () => {',a)
s=s[:a]+"""  const deleteItem = async (itemId: string): Promise<boolean> => {
    if (!activeBusinessId) return false;
    const item=items.find((i)=>i.itemId===itemId); if(!item)return false;
    if(!await supabaseSyncService.deleteItem(itemId)){setErrorMessage('Barang gagal dihapus dari database. Data lokal tidak diubah.');return false;}
    addDeletedItemId(itemId);
    setItems((prev)=>{const next=prev.filter((i)=>i.itemId!==itemId).map((r)=>r.bomIngredients?.some((x)=>x.rawItemId===itemId)?{...r,bomIngredients:r.bomIngredients.filter((x)=>x.rawItemId!==itemId),updatedAt:Date.now()}:r);saveStored('items',next);return next;});
    setOutletStocks((prev)=>{const next=prev.filter((x)=>x.itemId!==itemId);saveStored('outlet_stocks',next);return next;});
    setPosCart((prev)=>prev.filter((x)=>x.item.itemId!==itemId));
    addAuditLog('DELETE_ITEM',`Dihapus permanen: Item '${item.name}' (${item.sku}) dari database dan stok`,activeBusinessId);
    setUserMessage(`Item '${item.name}' berhasil dihapus permanen dari database.`);return true;
  };
""" + s[b:]
a=s.index('  const deleteOutlet = (outletId: string): boolean => {');b=s.index('\n  const transferStockToStan = (',a)
s=s[:a]+"""  const deleteOutlet = async (outletId: string): Promise<boolean> => {
    if(!currentSession)return false;
    const role=normalizeUserRole(currentSession.user.role);
    if(![UserRole.OWNER,UserRole.ADMIN_OWNER,UserRole.ADMIN_DIVISI].includes(role)){setErrorMessage('Hanya OWNER atau ADMIN yang dapat menghapus STAN/Outlet.');return false;}
    const target=outlets.find((o)=>o.outletId===outletId);if(!target){setErrorMessage('STAN/Outlet tidak ditemukan atau sudah dihapus.');return false;}
    const allowed=role===UserRole.OWNER?target.ownerId===currentSession.user.userId:role===UserRole.ADMIN_OWNER?(currentSession.user.assignedBusinessIds||[]).includes(target.businessId):target.businessId===currentSession.user.businessId||(currentSession.user.assignedBusinessIds||[]).includes(target.businessId);
    if(!allowed){setErrorMessage('Anda tidak berwenang menghapus STAN/Outlet dari bisnis ini.');return false;}
    if(!await supabaseSyncService.deleteOutlet(outletId)){setErrorMessage('STAN gagal dihapus dari database. Data lokal tidak diubah.');return false;}
    setOutlets((p)=>p.filter((x)=>x.outletId!==outletId));setOutletStocks((p)=>p.filter((x)=>x.outletId!==outletId));setStanTransfers((p)=>p.filter((x)=>x.outletId!==outletId));
    setUsers((p)=>p.map((u)=>u.outletId===outletId?{...u,outletId:null}:u));
    if(currentSession.user.outletId===outletId){setCurrentSession((p)=>p?{...p,user:{...p.user,outletId:null},staffBinding:p.staffBinding?{...p.staffBinding,outletId:null}:p.staffBinding}:p);setPosCart([]);}
    addAuditLog('DELETE_OUTLET',`Deleted permanently STAN/Outlet: ${target.name}`,target.businessId);setUserMessage(`STAN '${target.name}' berhasil dihapus permanen dari database.`);return true;
  };
""" + s[b:]
# The SQL sale-delete RPC now restores stock atomically; update only the in-memory view here.
a=s.index('    const changedAt = Date.now();',s.index('  const deleteOwnerSale ='));b=s.index('    setSales((prev) => prev.filter',a)
s=s[:a]+"""    const changedAt=Date.now();
    if(target.outletId){setOutletStocks((p)=>p.map((stock)=>{if(stock.outletId!==target.outletId||stock.businessId!==target.businessId)return stock;const line=(target.items||[]).find((x)=>x.itemId===stock.itemId);const item=items.find((x)=>x.itemId===stock.itemId);return !line||item?.type==='SERVICE'?stock:{...stock,stockQuantity:stock.stockQuantity+line.quantity,updatedAt:changedAt};}));}
    else{setItems((p)=>p.map((item)=>{const line=(target.items||[]).find((x)=>x.itemId===item.itemId);return !line||item.businessId!==target.businessId||item.type==='SERVICE'?item:{...item,stockQuantity:item.stockQuantity+line.quantity,updatedAt:changedAt};}));}
""" + s[b:]
s=s.replace("!(ledger.businessId === target.businessId && ledger.referenceId === target.receiptNumber)","!(ledger.businessId === target.businessId && [target.receiptNumber, target.saleId].includes(ledger.referenceId))",1)
p.write_text(s,encoding='utf-8')
# Confirm delete dialogs only close after the server confirms deletion.
rep('src/screens/InventoryScreen.tsx',"""                onClick={() => {
                  deleteItem(itemToDelete.itemId);
                  setItemToDelete(null);
                }}""","""                onClick={async () => {
                  const ok=await deleteItem(itemToDelete.itemId);
                  if(ok)setItemToDelete(null);
                }}""",'inventory dialog')
rep('src/screens/StanOutletScreen.tsx',"""                        onClick={() => {
                          if (confirm(`Hapus STAN "${outlet.name}"?`)) {
                            deleteOutlet(outlet.outletId);
                          }
                        }}""","""                        onClick={async () => {
                          if(confirm(`Hapus STAN "${outlet.name}"?`))await deleteOutlet(outlet.outletId);
                        }}""",'outlet dialog')
p=root/'src/services/supabaseSyncService.ts';s=p.read_text(encoding='utf-8')
a=s.index('  private async markRecordDeleted(');b=s.index('  public async flushPendingSync()',a);s=s[:a]+s[b:]
a=s.index('  public async deleteUserAccount(userId: string): Promise<boolean> {');b=s.index('  public async syncOperationalPeriod(',a)
s=s[:a]+"""  public async deleteUserAccount(userId:string):Promise<boolean>{
    const db=getSupabaseClient();if(!db||!userId)return false;
    try{const {data,error}=await db.from('users').delete().eq('user_id',userId).select('user_id');if(error)throw error;if(!data?.length)throw new Error('Akun tidak ditemukan atau penghapusan ditolak database.');this.clearPendingSyncForRecord('users',userId);if(this.channel)this.channel.send({type:'broadcast',event:'tgp_mutation',payload:{type:'DELETE',table:'users',id:userId}});return true;}
    catch(e){console.warn('[SupabaseSync] deleteUserAccount failed:',e);return false;}
  }

""" + s[b:]
a=s.index('  public async deleteItem(itemId: string): Promise<boolean> {');b=s.index('  public async syncTransfer(',a)
s=s[:a]+"""  public async deleteItem(itemId:string):Promise<boolean>{
    const db=getSupabaseClient();if(!db||!itemId)return false;
    try{const {data,error}=await db.rpc('delete_tgp_item',{p_item_id:itemId});if(error)throw error;if(!data?.success||Number(data.item_rows_deleted)!==1)throw new Error('Database tidak mengonfirmasi penghapusan barang.');this.clearPendingSyncForRecord('items',itemId);for(const id of (Array.isArray(data.stock_ids)?data.stock_ids:[]))this.clearPendingSyncForRecord('outlet_stocks',String(id));if(this.channel)this.channel.send({type:'broadcast',event:'tgp_mutation',payload:{type:'DELETE_ITEM',itemId}});return true;}
    catch(e){console.warn('[SupabaseSync] deleteItem failed:',e);return false;}
  }

""" + s[b:]
a=s.index('  public async deleteOutlet(outletId: string): Promise<boolean> {');b=s.index('  public async syncOutletStock(',a)
s=s[:a]+"""  public async deleteOutlet(outletId:string):Promise<boolean>{
    const db=getSupabaseClient();if(!db||!outletId)return false;
    try{const {data,error}=await db.rpc('delete_tgp_outlet',{p_outlet_id:outletId});if(error)throw error;if(!data?.success||Number(data.outlet_rows_deleted)!==1)throw new Error('Database tidak mengonfirmasi penghapusan STAN.');this.clearPendingSyncForRecord('outlets',outletId);for(const id of (Array.isArray(data.stock_ids)?data.stock_ids:[]))this.clearPendingSyncForRecord('outlet_stocks',String(id));for(const id of (Array.isArray(data.stan_transfer_ids)?data.stan_transfer_ids:[]))this.clearPendingSyncForRecord('stan_transfers',String(id));for(const id of (Array.isArray(data.mutation_ids)?data.mutation_ids:[]))this.clearPendingSyncForRecord('stock_mutations',String(id));if(this.channel)this.channel.send({type:'broadcast',event:'tgp_mutation',payload:{type:'DELETE_OUTLET',outletId}});return true;}
    catch(e){console.warn('[SupabaseSync] deleteOutlet failed:',e);return false;}
  }

""" + s[b:]
p.write_text(s,encoding='utf-8')
