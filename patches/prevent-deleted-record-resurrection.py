from pathlib import Path
import re

root = Path("project")
ctx = root / "src/context/TgpContext.tsx"
sync = root / "src/services/supabaseSyncService.ts"

# Local snapshot recovery re-inserted rows intentionally deleted from Supabase.
# Keep initial seeding, but never upload the entire local cache back into the database.
s = ctx.read_text()
pattern = re.compile(
    r"    // Seed initial data if DB is empty, then recover local records missing on the server\.[\s\S]*?\n    \}\)\.catch\(\(error\) => console\.warn\('\[cross-device\] local recovery failed', error\)\);",
    re.M
)
if pattern.search(s):
    s = pattern.sub("""    // Seed only the application's initial data when the database is empty.
    // Never reconcile stale browser snapshots into Supabase: deleted rows must stay deleted.
    void supabaseSyncService.seedInitialData({
      businesses: INITIAL_BUSINESSES,
      users: INITIAL_USERS,
      items: INITIAL_ITEMS,
      ledgers: INITIAL_LEDGERS,
      sales: INITIAL_SALES,
      transfers: INITIAL_TRANSFERS,
      damaged: INITIAL_DAMAGED,
      auditLogs: INITIAL_AUDIT_LOGS,
    });""", s, count=1)
    ctx.write_text(s)
    print("Removed local-snapshot resurrection path")
elif "local recovery failed" not in s and "reconcileLocalSnapshot({" not in s:
    print("Local snapshot reconciliation already absent")
else:
    raise RuntimeError("Could not safely remove startup local-snapshot reconciliation")

# A DELETE returning no rows (for example because RLS blocked it) is not success.
s = sync.read_text()
start = s.find("  public async deleteUserAccount(userId: string): Promise<boolean> {")
end = s.find("  public async syncOperationalPeriod(", start)
if start < 0 or end < 0:
    raise RuntimeError("deleteUserAccount method boundaries missing")
new_method = """  public async deleteUserAccount(userId: string): Promise<boolean> {
    const supabase = getSupabaseClient();
    if (!supabase || !userId) return false;
    try {
      const { data: deletedUsers, error } = await supabase
        .from('users')
        .delete()
        .eq('user_id', userId)
        .select('user_id');
      if (error) throw error;
      if (!deletedUsers || deletedUsers.length === 0) {
        throw new Error('Akun tidak ditemukan di Supabase atau penghapusan ditolak oleh kebijakan akses.');
      }
      if (this.channel) {
        this.channel.send({ type: 'broadcast', event: 'tgp_mutation', payload: { type: 'DELETE', table: 'users', id: userId } });
      }
      return true;
    } catch (error) {
      console.warn('[SupabaseSync] deleteUserAccount failed:', error);
      return false;
    }
  }

"""
s = s[:start] + new_method + s[end:]
sync.write_text(s)
print("Hardened employee deletion: requires an actual deleted row")
