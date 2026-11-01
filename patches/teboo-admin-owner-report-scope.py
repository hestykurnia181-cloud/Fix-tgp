from pathlib import Path

ROOT = Path('project')
TEBOO_ID = 'biz-1790060935868'

def replace_once(path, old, new, label):
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if new in s:
        return
    if old not in s:
        raise SystemExit(f'Missing required anchor ({label}) in {path}')
    p.write_text(s.replace(old, new, 1), encoding='utf-8')

replace_once(
    'src/types.ts',
    '  createdBy: string;\n  periodId?: string;\n',
    '  createdBy: string;\n  createdByUserId?: string;\n  periodId?: string;\n',
    'ledger actor ID type'
)
replace_once(
    'src/services/supabaseSyncService.ts',
    '    createdBy: row.created_by,\n    timestamp: Number(row.timestamp),\n    periodId: row.period_id || undefined,\n',
    '    createdBy: row.created_by,\n    createdByUserId: row.created_by_user_id || undefined,\n    timestamp: Number(row.timestamp),\n    periodId: row.period_id || undefined,\n',
    'ledger actor ID database mapping'
)
replace_once(
    'src/services/supabaseSyncService.ts',
    '    created_by: entity.createdBy,\n    timestamp: entity.timestamp,\n    period_id: (entity as any).periodId || null,\n',
    '    created_by: entity.createdBy,\n    created_by_user_id: entity.createdByUserId || null,\n    timestamp: entity.timestamp,\n    period_id: (entity as any).periodId || null,\n',
    'ledger actor ID persistence mapping'
)

# Stamp every new ledger record with the immutable account ID.
p = ROOT / 'src/context/TgpContext.tsx'
s = p.read_text(encoding='utf-8')
patterns = [
    ('createdBy: currentSession.user.fullName,', 'createdBy: currentSession.user.fullName,\n        createdByUserId: currentSession.user.userId,'),
    ('createdBy: currentSession.user.username,', 'createdBy: currentSession.user.username,\n      createdByUserId: currentSession.user.userId,'),
    ("createdBy: currentSession?.user.fullName || currentSession?.user.username || 'owner',", "createdBy: currentSession?.user.fullName || currentSession?.user.username || 'owner',\n      createdByUserId: currentSession?.user.userId,"),
    ("createdBy: currentSession?.user.username || 'owner',", "createdBy: currentSession?.user.username || 'owner',\n      createdByUserId: currentSession?.user.userId,"),
    ("createdBy: currentSession.user.fullName || currentSession.user.username || 'staff',", "createdBy: currentSession.user.fullName || currentSession.user.username || 'staff',\n      createdByUserId: currentSession.user.userId,"),
]
for old, new in patterns:
    s = s.replace(old, new)
if 'createdByUserId:' not in s:
    raise SystemExit('Failed to stamp ledger actor IDs')
p.write_text(s, encoding='utf-8')

# Scope reports only when the selected business is Teboo and the actor is Admin Owner.
replace_once(
    'src/screens/ReportsScreen.tsx',
    "  const isSekapBungo = activeBusiness?.businessId === 'biz-1790060286099';\n",
    "  const isSekapBungo = activeBusiness?.businessId === 'biz-1790060286099';\n"
    f"  const isTebooAdminOwner = activeBusiness?.businessId === '{TEBOO_ID}' && role === UserRole.ADMIN_OWNER;\n"
    "  const currentActorId = currentSession?.user.userId;\n",
    'Teboo Admin Owner scope flag'
)
replace_once(
    'src/screens/ReportsScreen.tsx',
    "      if (isSekapBungo && (!sale.outletId || !activeOutletIds.has(sale.outletId))) return false;\n      if (!isCashier) return true;\n",
    "      if (isSekapBungo && (!sale.outletId || !activeOutletIds.has(sale.outletId))) return false;\n"
    "      if (isTebooAdminOwner && sale.cashierUserId !== currentActorId) return false;\n"
    "      if (!isCashier) return true;\n",
    'Teboo Admin Owner sales actor filter'
)
replace_once(
    'src/screens/ReportsScreen.tsx',
    '  }, [activeSales, sales, activeOutletIds, isSekapBungo, activeBusiness?.businessId, currentSession?.user.userId, currentSession?.user.fullName, isCashier]);',
    '  }, [activeSales, sales, activeOutletIds, isSekapBungo, isTebooAdminOwner, currentActorId, activeBusiness?.businessId, currentSession?.user.userId, currentSession?.user.fullName, isCashier]);',
    'Teboo Admin Owner sales dependencies'
)

addition = """  const filteredTebooAdminLedgers = useMemo(() => {
    if (!isTebooAdminOwner || !currentActorId) return [];
    const now = new Date();
    const todayStart = new Date(now); todayStart.setHours(0, 0, 0, 0);
    const weekStart = startOfWeek(now);
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    return periodLedgers.filter((entry) => {
      if (entry.businessId !== activeBusiness?.businessId || entry.createdByUserId !== currentActorId) return false;
      const time = Number(entry.timestamp || entry.date || 0);
      if (!time) return false;
      if (dateFilter === 'ALL') return true;
      if (dateFilter === 'TODAY') return time >= todayStart.getTime();
      if (dateFilter === 'WEEK') return time >= weekStart.getTime();
      return time >= monthStart.getTime();
    });
  }, [periodLedgers, activeBusiness?.businessId, isTebooAdminOwner, currentActorId, dateFilter]);

  const tebooAdminNetBalance = filteredTebooAdminLedgers.reduce(
    (balance, entry) => balance + (entry.type === 'PEMASUKAN' ? Number(entry.amount || 0) : -Number(entry.amount || 0)),
    0
  );

"""
p = ROOT / 'src/screens/ReportsScreen.tsx'
s = p.read_text(encoding='utf-8')
anchor = '  // Group ledger entries by their own STAN and apply the selected report period.\n'
if addition not in s:
    if anchor not in s:
        raise SystemExit('Missing report ledger insertion anchor')
    p.write_text(s.replace(anchor, addition + anchor, 1), encoding='utf-8')

replace_once(
    'src/screens/ReportsScreen.tsx',
    "      if (isSekapBungo && !activeOutletIds.has(entry.outletId)) return false;\n      if (isCashier && entry.outletId !== currentSession?.user.outletId) return false;",
    "      if (isSekapBungo && !activeOutletIds.has(entry.outletId)) return false;\n      if (isTebooAdminOwner && entry.createdByUserId !== currentActorId) return false;\n      if (isCashier && entry.outletId !== currentSession?.user.outletId) return false;",
    'Teboo Admin Owner STAN ledger actor filter'
)
replace_once(
    'src/screens/ReportsScreen.tsx',
    '  }, [periodLedgers, activeBusiness?.businessId, activeOutletIds, isSekapBungo, isCashier, currentSession?.user.outletId, dateFilter]);',
    '  }, [periodLedgers, activeBusiness?.businessId, activeOutletIds, isSekapBungo, isTebooAdminOwner, currentActorId, isCashier, currentSession?.user.outletId, dateFilter]);',
    'Teboo Admin Owner STAN ledger dependencies'
)

replace_once(
    'src/screens/ReportsScreen.tsx',
    'value={formatRupiah(isSekapBungo ? stanNetTotal : activeBusinessFinance.netBalance)}',
    'value={formatRupiah(isSekapBungo ? stanNetTotal : isTebooAdminOwner ? tebooAdminNetBalance : activeBusinessFinance.netBalance)}',
    'Teboo Admin Owner net balance'
)
replace_once(
    'src/screens/ReportsScreen.tsx',
    "color={(isSekapBungo ? stanNetTotal : activeBusinessFinance.netBalance) >= 0 ? 'blue' : 'rose'}",
    "color={(isSekapBungo ? stanNetTotal : isTebooAdminOwner ? tebooAdminNetBalance : activeBusinessFinance.netBalance) >= 0 ? 'blue' : 'rose'}",
    'Teboo Admin Owner net balance color'
)
replace_once(
    'src/screens/ReportsScreen.tsx',
    'subtitle={isSekapBungo ? "Akumulasi Sisa Bersih seluruh STAN aktif" : "Khusus OWNER / ADMIN OWNER"}',
    'subtitle={isSekapBungo ? "Akumulasi Sisa Bersih seluruh STAN aktif" : isTebooAdminOwner ? "Akumulasi transaksi yang dicatat akun ini" : "Khusus OWNER / ADMIN OWNER"}',
    'Teboo Admin Owner net balance subtitle'
)

replace_once(
    'src/screens/AuditLogViewerScreen.tsx',
    "  const { auditLogs } = useTgp();\n  const [searchTerm, setSearchTerm] = useState('');\n\n  const filteredLogs = auditLogs.filter(\n    (l) =>\n      l.action.toLowerCase().includes(searchTerm.toLowerCase()) ||\n      l.username.toLowerCase().includes(searchTerm.toLowerCase()) ||\n      l.details.toLowerCase().includes(searchTerm.toLowerCase()) ||\n      (l.role && l.role.toLowerCase().includes(searchTerm.toLowerCase()))\n  );",
    "  const { auditLogs, activeBusiness, currentSession } = useTgp();\n  const [searchTerm, setSearchTerm] = useState('');\n  const isTebooAdminOwner = activeBusiness?.businessId === 'biz-1790060935868' && currentSession?.user.role === 'ADMIN_OWNER';\n\n  const filteredLogs = auditLogs.filter(\n    (l) => (!isTebooAdminOwner || (l.businessId === activeBusiness?.businessId && l.userId === currentSession?.user.userId)) &&\n      (l.action.toLowerCase().includes(searchTerm.toLowerCase()) ||\n      l.username.toLowerCase().includes(searchTerm.toLowerCase()) ||\n      l.details.toLowerCase().includes(searchTerm.toLowerCase()) ||\n      (l.role && l.role.toLowerCase().includes(searchTerm.toLowerCase())))\n  );",
    'Teboo Admin Owner audit actor filter'
)

print('Applied Teboo-only Admin Owner report and audit isolation using exact user IDs.')
