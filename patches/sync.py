from pathlib import Path
import re
p=Path("project/src/services/supabaseSyncService.ts")
s=p.read_text()
if "safeUpsertRecord" not in s:
    if "this.upsertRecord(" not in s:
        raise RuntimeError("sync anchor missing")
    s=s.replace("this.upsertRecord(","this.safeUpsertRecord(")
    m=re.search(r"(\n\s*)(?:(?:public|private|protected)\s+)?async\s+upsertRecord\s*\(",s)
    if not m: raise RuntimeError("upsertRecord declaration missing")
    s=s[:m.start()]+s[m.start():m.end()].replace("upsertRecord","rawUpsertRecord",1)+s[m.end():]
    helper=r'''
  private readPendingSync(): any[] {
    try {
      const raw=typeof window==='undefined' ? '' : window.localStorage.getItem('tgp_pending_sync_v2');
      const rows=raw ? JSON.parse(raw) : [];
      return Array.isArray(rows) ? rows : [];
    } catch { return []; }
  }
  private writePendingSync(rows:any[]) {
    if(typeof window!=='undefined') window.localStorage.setItem('tgp_pending_sync_v2',JSON.stringify(rows.slice(-500)));
  }
  private queuePendingSync(table:string,data:any) {
    const rows=this.readPendingSync();
    const id=table+':'+String(data?.id||data?.sale_id||data?.period_id||data?.user_id||JSON.stringify(data));
    this.writePendingSync([...rows.filter((x:any)=>x.id!==id),{id,table,data}]);
  }
  private async safeUpsertRecord(table:string,data:any) {
    if(typeof navigator!=='undefined' && !navigator.onLine){ this.queuePendingSync(table,data); return; }
    try { await this.rawUpsertRecord(table,data); } catch(error) {
      this.queuePendingSync(table,data);
      console.warn('[TGP sync] queued operation',table,error);
    }
  }
  public async flushPendingSync() {
    if(typeof navigator!=='undefined' && !navigator.onLine) return;
    const rows=this.readPendingSync(); const keep:any[]=[];
    for(const row of rows) {
      try { await this.rawUpsertRecord(row.table,row.data); } catch { keep.push(row); }
    }
    this.writePendingSync(keep);
  }

'''
    marker=s.find("\n  public async sync")
    if marker<0: marker=s.find("\n  async sync")
    if marker<0: raise RuntimeError("sync method anchor missing")
    s=s[:marker]+"\n"+helper+s[marker:]
p.write_text(s)
print("sync queue patch applied")
