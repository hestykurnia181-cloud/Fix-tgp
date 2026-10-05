from pathlib import Path
import re

root = Path("project")

ctx = root / "src/context/TgpContext.tsx"
s = ctx.read_text()
s = s.replace(
    "  changeOwnerPassword: (currentPassword: string, newPassword: string, confirmPassword: string) => boolean;\n",
    "  changeOwnerPassword: (currentPassword: string, newPassword: string, confirmPassword: string) => boolean;\n"
    "  resetUserPassword: (userId: string, newPassword: string, confirmPassword: string) => Promise<boolean>;\n",
    1,
)
anchor = "  const resetMasterAccount = () => {\n"
fn = """  const resetUserPassword = async (userId: string, newPassword: string, confirmPassword: string): Promise<boolean> => {
    const actor = currentSession?.user;
    const actorRole = actor ? normalizeUserRole(actor.role) : null;
    if (!actor || (actorRole !== UserRole.MASTER && actorRole !== UserRole.ADMIN_OWNER)) {
      setErrorMessage('Anda tidak memiliki akses untuk mengubah password akun pengguna lain.');
      return false;
    }
    const target = users.find((u) => u.userId === userId);
    if (!target) {
      setErrorMessage('Akun yang akan diubah tidak ditemukan.');
      return false;
    }
    if (actorRole === UserRole.ADMIN_OWNER) {
      const targetRole = normalizeUserRole(target.role);
      const targetIsEmployee =
        targetRole === UserRole.STAFF ||
        targetRole === UserRole.KASIR ||
        targetRole === UserRole.WAREHOUSE ||
        targetRole === UserRole.ADMIN_DIVISI;
      const actorBusinessIds = new Set<string>([
        ...(actor.assignedBusinessIds || []),
        ...(actor.businessId ? [actor.businessId] : []),
      ]);
      const targetBusinessIds = new Set<string>([
        ...(target.assignedBusinessIds || []),
        ...(target.businessId ? [target.businessId] : []),
      ]);
      const sameBusiness = [...actorBusinessIds].some((id) => targetBusinessIds.has(id));
      if (!targetIsEmployee || !sameBusiness) {
        setErrorMessage('Admin Owner hanya dapat mengubah password karyawan yang berada di bisnisnya.');
        return false;
      }
    }

    if (!newPassword || newPassword.length < 6) {
      setErrorMessage('Password baru minimal 6 karakter.');
      return false;
    }
    if (newPassword !== confirmPassword) {
      setErrorMessage('Konfirmasi password baru tidak sama.');
      return false;
    }
    const updatedUser: UserEntity = { ...target, passwordHash: newPassword };
    try {
      const synced = await supabaseSyncService.syncUser(updatedUser);
      if (!synced) {
        setErrorMessage('Password gagal disimpan ke Supabase. Perubahan lokal dibatalkan.');
        return false;
      }
    } catch (error: any) {
      setErrorMessage(`Password gagal disimpan: ${error?.message || 'Error tidak diketahui'}`);
      return false;
    }
    setUsers((prev) => prev.map((u) => (u.userId === userId ? updatedUser : u)));
    if (currentSession?.user.userId === userId) {
      setCurrentSession((prev) => (prev ? { ...prev, user: updatedUser } : prev));
    }
    const auditAction = actorRole === UserRole.ADMIN_OWNER ? 'ADMIN_OWNER_EMPLOYEE_PASSWORD_CHANGED' : 'MASTER_USER_PASSWORD_CHANGED';
    addAuditLog(auditAction, `${actor.role} (${actor.username}) changed password for ${target.username}.`);
    setUserMessage(`Password akun ${target.username} berhasil diubah.`);
    return true;
  };

"""
if "const resetUserPassword = async" not in s:
    s = s.replace(anchor, fn + anchor, 1)
s = s.replace("        changeOwnerPassword,\n", "        changeOwnerPassword,\n        resetUserPassword,\n", 1)
ctx.write_text(s)

ui = root / "src/screens/MasterDashboardScreen.tsx"
s = ui.read_text()
s = s.replace("  Users,\n", "  Users,\n  KeyRound,\n  X,\n", 1)
s = s.replace("    supabaseStatus,\n", "    supabaseStatus,\n    resetUserPassword,\n", 1)
s = s.replace(
    "  const [activeTab, setActiveTab] = useState<'BUSINESSES' | 'USERS'>('BUSINESSES');\n",
    "  const [activeTab, setActiveTab] = useState<'BUSINESSES' | 'USERS'>('BUSINESSES');\n"
    "  const [selectedUser, setSelectedUser] = useState<(typeof users)[number] | null>(null);\n"
    "  const [newPassword, setNewPassword] = useState('');\n"
    "  const [confirmPassword, setConfirmPassword] = useState('');\n"
    "  const [isSavingPassword, setIsSavingPassword] = useState(false);\n",
    1,
)
old = """                  <div className="text-left sm:text-right shrink-0">
                    <span className="text-[11px] text-slate-500 block">
                      {u.assignedBusinessIds?.length
                        ? `${u.assignedBusinessIds.length} Bisnis Ditugaskan`
                        : u.businessId
                        ? '1 Bisnis Terikat'
                        : 'Akses Platform'}
                    </span>
                  </div>
"""
new = """                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[11px] text-slate-500 hidden sm:block">
                      {u.assignedBusinessIds?.length
                        ? `${u.assignedBusinessIds.length} Bisnis Ditugaskan`
                        : u.businessId
                        ? '1 Bisnis Terikat'
                        : 'Akses Platform'}
                    </span>
                    <button
                      type="button"
                      onClick={() => { setSelectedUser(u); setNewPassword(''); setConfirmPassword(''); }}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-[11px] font-bold flex items-center gap-1.5"
                      data-testid={`btn_user_details_${u.userId}`}
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      Detail / Password
                    </button>
                  </div>
"""
if old in s:
    s = s.replace(old, new, 1)
modal_anchor = "      <CreateBusinessDialog\n"
modal = """      {selectedUser && (
        <div className="fixed inset-0 z-[80] bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] uppercase tracking-wider font-extrabold text-indigo-600">Detail Akun Pengguna</p>
                <h3 className="text-lg font-extrabold text-slate-900 mt-1">{selectedUser.fullName}</h3>
                <p className="text-xs text-slate-500 mt-1">Admin Master dapat melihat metadata akun dan menetapkan password baru.</p>
              </div>
              <button type="button" onClick={() => setSelectedUser(null)} className="p-2 rounded-xl hover:bg-slate-100" aria-label="Tutup"><X className="w-5 h-5 text-slate-500" /></button>
            </div>
            <div className="p-5 space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-3"><p className="text-[10px] text-slate-400 font-bold uppercase">Email / Username</p><p className="text-sm font-bold text-slate-800 break-all mt-1">{selectedUser.username}</p></div>
                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-3"><p className="text-[10px] text-slate-400 font-bold uppercase">Peran</p><p className="text-sm font-bold text-slate-800 mt-1">{selectedUser.role}</p></div>
                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-3"><p className="text-[10px] text-slate-400 font-bold uppercase">User ID</p><p className="text-xs font-mono text-slate-700 break-all mt-1">{selectedUser.userId}</p></div>
                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-3"><p className="text-[10px] text-slate-400 font-bold uppercase">Dibuat</p><p className="text-sm font-bold text-slate-800 mt-1">{new Date(selectedUser.createdAt).toLocaleString('id-ID')}</p></div>
              </div>
              <div className="rounded-2xl bg-indigo-50 border border-indigo-100 p-4">
                <div className="flex items-center gap-2 mb-2"><KeyRound className="w-4 h-4 text-indigo-600" /><p className="text-xs font-extrabold text-indigo-900">Ubah / Reset Password</p></div>
                <p className="text-[11px] text-indigo-700 mb-3">Password lama tidak ditampilkan. Masukkan password baru untuk akun ini.</p>
                <div className="space-y-2">
                  <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="Password baru (min. 6 karakter)" className="w-full px-3 py-2.5 rounded-xl border border-indigo-200 text-sm bg-white" autoComplete="new-password" />
                  <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Konfirmasi password baru" className="w-full px-3 py-2.5 rounded-xl border border-indigo-200 text-sm bg-white" autoComplete="new-password" />
                </div>
                <button type="button" disabled={isSavingPassword || newPassword.length < 6 || newPassword !== confirmPassword}
                  onClick={async () => {
                    setIsSavingPassword(true);
                    const ok = await resetUserPassword(selectedUser.userId, newPassword, confirmPassword);
                    setIsSavingPassword(false);
                    if (ok) { setNewPassword(''); setConfirmPassword(''); setSelectedUser(null); }
                  }}
                  className="w-full mt-3 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-extrabold"
                  data-testid="btn_master_save_user_password"
                >
                  {isSavingPassword ? 'Menyimpan...' : 'Simpan Password Baru'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

"""
if "Detail Akun Pengguna" not in s:
    s = s.replace(modal_anchor, modal + modal_anchor, 1)
ui.write_text(s)


# Admin Owner: add a password action to the Karyawan list.
for screen in (root / "src/screens").rglob("*.tsx"):
    try:
        t = screen.read_text()
    except Exception:
        continue
    if "Karyawan" not in t or "useTgp" not in t:
        continue
    if "btn_admin_owner_employee_password" in t:
        break
    if not re.search(r"users(?:\.filter\([^\n]+\))?\.map\(\(u\)", t):
        continue

    if "KeyRound" not in t and "from 'lucide-react'" in t:
        t = re.sub(
            r"(import\s*\{)([\s\S]*?)(\}\s*from\s*['\"]lucide-react['\"])",
            lambda m: m.group(1) + m.group(2) + "\n  KeyRound," + m.group(3),
            t, count=1
        )

    if "resetUserPassword" not in t:
        t = re.sub(
            r"(const\s*\{[\s\S]*?)(\n\s*\}\s*=\s*useTgp\(\);)",
            lambda m: m.group(1) + "\n    resetUserPassword," + m.group(2),
            t, count=1
        )

    pattern = r"(users(?:\.filter\([^\n]+\))?\.map\(\(u\)\s*=>\s*\(\s*<div[^>]*>)"
    def add_button(m):
        return m.group(1) + """
                    <button
                      type="button"
                      onClick={async () => {
                        const nextPassword = window.prompt('Password baru untuk ' + u.username + '\\nMinimal 6 karakter:');
                        if (nextPassword === null) return;
                        if (nextPassword.length < 6) {
                          window.alert('Password baru minimal 6 karakter.');
                          return;
                        }
                        const confirmPassword = window.prompt('Ulangi password baru:');
                        if (confirmPassword === null) return;
                        const ok = await resetUserPassword(u.userId, nextPassword, confirmPassword);
                        if (ok) window.alert('Password karyawan berhasil diperbarui.');
                      }}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-[11px] font-bold inline-flex items-center gap-1.5"
                      data-testid={"btn_admin_owner_employee_password_" + u.userId}
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      Ganti Password
                    </button>
"""
    t2, n = re.subn(pattern, add_button, t, count=1)

    if n == 0:
        pattern2 = r"(users(?:\.filter\([^\n]+\))?\.map\(\(u\)[\s\S]{0,700}?)(\{u\.username\})"
        def add_before_username(m):
            return m.group(1) + """
                      <button
                        type="button"
                        onClick={async () => {
                          const nextPassword = window.prompt('Password baru untuk ' + u.username + '\\nMinimal 6 karakter:');
                          if (nextPassword === null) return;
                          if (nextPassword.length < 6) { window.alert('Password baru minimal 6 karakter.'); return; }
                          const confirmPassword = window.prompt('Ulangi password baru:');
                          if (confirmPassword === null) return;
                          const ok = await resetUserPassword(u.userId, nextPassword, confirmPassword);
                          if (ok) window.alert('Password karyawan berhasil diperbarui.');
                        }}
                        className="ml-2 px-2.5 py-1 rounded-lg bg-indigo-600 text-white text-[11px] font-bold"
                        data-testid={"btn_admin_owner_employee_password_" + u.userId}
                      >
                        Ganti Password
                      </button>
""" + m.group(2)
        t, n = re.subn(pattern2, add_before_username, t, count=1)
    else:
        t = t2

    if n:
        screen.write_text(t)
        print("Admin Owner password action patched:", screen)
        break
else:
    print("WARNING: Admin Owner Karyawan screen was not patched.")
