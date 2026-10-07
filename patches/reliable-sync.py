from pathlib import Path
import re

p = Path("project/src/services/supabaseSyncService.ts")
if not p.exists():
    raise RuntimeError("supabaseSyncService.ts not found")
s = p.read_text()

pattern = r'(const \{ error \} = await supabase\.from\(table\)\.upsert\(dbPayload\);\s*if \(error\) \{\s*console\.warn\([^\n]+\);)'
if "throw error;" not in s:
    m = re.search(pattern, s)
    if not m:
        raise RuntimeError("Supabase upsert error handler anchor not found")
    s = s[:m.end()] + "\n        throw error;" + s[m.end():]

if "public startPendingSyncRetry()" not in s:
    marker = "  public async flushPendingSync() {"
    if marker not in s:
        raise RuntimeError("flushPendingSync anchor not found")
    s = s.replace(marker, """  public startPendingSyncRetry() {
    if (typeof window === 'undefined') return;
    const retry = () => { void this.flushPendingSync(); };
    window.addEventListener('online', retry);
    if (navigator.onLine) retry();
  }

  public async flushPendingSync() {""", 1)

if "this.startPendingSyncRetry();" not in s and "    this.startRealtimeSync();" in s:
    s = s.replace("    this.startRealtimeSync();", "    this.startRealtimeSync();\n    this.startPendingSyncRetry();", 1)

p.write_text(s)
print("Reliable Supabase sync patch applied")
