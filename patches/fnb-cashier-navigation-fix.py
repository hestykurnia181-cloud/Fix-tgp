from pathlib import Path

root = Path('project')
bottom = root / 'src/components/TgpBottomBar.tsx'
context = root / 'src/context/TgpContext.tsx'
if not bottom.exists() or not context.exists():
    raise SystemExit('FNB cashier navigation fix: required source files were not found')

text = bottom.read_text()
text = text.replace(
    "const { currentSession, activeBusiness, activeOutlets, activeScreen, navigateTo, pendingTransfersForOwner, pendingDamagedForOwner, pendingStanReturnsForApproval } = useTgp();",
    "const { currentSession, activeBusiness, activeOutlets, activeScreen, navigateTo, pendingTransfersForOwner, pendingDamagedForOwner, pendingStanReturnsForApproval, businesses } = useTgp();"
)
text = text.replace(
    "  const role = currentSession.user.role as UserRole;\n  const totalPending = pendingTransfersForOwner.length + pendingDamagedForOwner.length + pendingStanReturnsForApproval.length;",
    "  const role = currentSession.user.role as UserRole;\n  const cashierBusinessId = currentSession.user.businessId || currentSession.user.assignedBusinessIds?.[0] || null;\n  const cashierBusiness = cashierBusinessId ? businesses.find((business) => business.businessId === cashierBusinessId) : null;\n  const isFnbCashier = activeBusiness?.templateType === 'FNB' || cashierBusiness?.templateType === 'FNB';\n  const hasAssignedActiveOutlet = !!currentSession.user.outletId && activeOutlets.some((outlet) => outlet.outletId === currentSession.user.outletId && outlet.status === 'ACTIVE');\n  const totalPending = pendingTransfersForOwner.length + pendingDamagedForOwner.length + pendingStanReturnsForApproval.length;"
)
text = text.replace(
    "...(activeBusiness?.templateType === 'FNB' && currentSession?.user.outletId ? [{ screen: 'CASHIER_STOCK_IN_MODULE' as AppScreen, label: 'Input Stok', icon: <PackagePlus className=\"w-5 h-5\" /> }, { screen: 'CASHIER_CLOSING_MODULE' as AppScreen, label: 'Closing', icon: <ClipboardCheck className=\"w-5 h-5\" /> }] : []),",
    "...(isFnbCashier && hasAssignedActiveOutlet ? [{ screen: 'CASHIER_STOCK_IN_MODULE' as AppScreen, label: 'Input Stok', icon: <PackagePlus className=\"w-5 h-5\" /> }, { screen: 'CASHIER_CLOSING_MODULE' as AppScreen, label: 'Closing', icon: <ClipboardCheck className=\"w-5 h-5\" /> }] : []),"
)
text = text.replace(
    '<div className="max-w-md mx-auto flex items-center justify-around h-16 px-3">',
    '<div className="max-w-md mx-auto flex items-center justify-start gap-1 h-16 px-3 overflow-x-auto">'
)
text = text.replace(
    'justify-center flex-1 h-full relative transition-colors',
    'justify-center flex-none min-w-[56px] px-1 h-full relative transition-colors'
)
if 'businesses } = useTgp()' not in text or 'isFnbCashier && hasAssignedActiveOutlet' not in text or 'overflow-x-auto' not in text:
    raise SystemExit('FNB cashier navigation fix: expected bottom navigation patterns were not found')
bottom.write_text(text)

text = context.read_text()
old = "      if (businesses.find((b)=>b.businessId===activeBusinessId)?.templateType===BusinessTemplate.FNB && currentSession.user.outletId) allowedScreens.push('CASHIER_STOCK_IN_MODULE','CASHIER_CLOSING_MODULE');"
new = "      const cashierBusinessId = currentSession.user.businessId || currentSession.user.assignedBusinessIds?.[0] || activeBusinessId;\n      const isAssignedActiveFnbOutlet = businesses.find((b) => b.businessId === cashierBusinessId)?.templateType === BusinessTemplate.FNB && !!currentSession.user.outletId && outlets.some((outlet) => outlet.outletId === currentSession.user.outletId && outlet.businessId === cashierBusinessId && outlet.status === 'ACTIVE');\n      if (isAssignedActiveFnbOutlet) allowedScreens.push('CASHIER_STOCK_IN_MODULE', 'CASHIER_CLOSING_MODULE');"
if old not in text:
    raise SystemExit('FNB cashier navigation fix: route authorization pattern was not found')
text = text.replace(old, new)
context.write_text(text)
print('FNB cashier navigation fix applied')


# Place stock input beside the STAN selector in the POS header.
pos = root / 'src/screens/PosScreen.tsx'
if not pos.exists():
    raise SystemExit('FNB cashier navigation fix: PosScreen.tsx was not found')
text = pos.read_text()
text = text.replace(
    "  Store,\n  Tag,",
    "  Store,\n  PackagePlus,\n  Tag,"
)
text = text.replace(
    "    checkout,\n    currentSession,",
    "    checkout,\n    currentSession,\n    navigateTo,"
)
old_header = """          <div className="flex items-center gap-2">
            <Store className="w-4 h-4 text-amber-600 shrink-0" />
            <select
              value={selectedOutletId}
              onChange={(e) => setSelectedOutletId(e.target.value)}
              disabled={!!userAssignedOutletId}
              className="px-3 py-1.5 rounded-xl border border-amber-300 bg-amber-50/60 text-xs font-bold text-amber-950 focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              {activeOutlets.map((o) => (
                <option key={o.outletId} value={o.outletId}>
                  Stand: {o.name} ({o.code})
                </option>
              ))}
            </select>
          </div>"""
new_header = """          <div className="flex items-center gap-2 flex-wrap">
            <Store className="w-4 h-4 text-amber-600 shrink-0" />
            <select
              value={selectedOutletId}
              onChange={(e) => setSelectedOutletId(e.target.value)}
              disabled={!!userAssignedOutletId}
              className="px-3 py-2 rounded-xl border border-amber-300 bg-amber-50/60 text-xs font-bold text-amber-950 focus:outline-none focus:ring-2 focus:ring-amber-500 max-w-full"
            >
              {activeOutlets.map((o) => (
                <option key={o.outletId} value={o.outletId}>
                  Stand: {o.name} ({o.code})
                </option>
              ))}
            </select>
            {activeBusiness?.templateType === 'FNB' && userAssignedOutletId && (
              <button
                type="button"
                onClick={() => navigateTo('CASHIER_STOCK_IN_MODULE')}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-blue-600 text-white text-xs font-extrabold shadow-sm hover:bg-blue-700 whitespace-nowrap"
              >
                <PackagePlus className="w-4 h-4" />
                Input Stok
              </button>
            )}
          </div>"""
if old_header not in text:
    raise SystemExit('FNB cashier navigation fix: POS STAN selector block was not found')
text = text.replace(old_header, new_header)
pos.write_text(text)

# For F&B cashiers, replace the Retur Stok bottom-nav destination with Closing.
text = bottom.read_text()
old = """      ...(isFnbCashier && hasAssignedActiveOutlet ? [{ screen: 'CASHIER_STOCK_IN_MODULE' as AppScreen, label: 'Input Stok', icon: <PackagePlus className="w-5 h-5" /> }, { screen: 'CASHIER_CLOSING_MODULE' as AppScreen, label: 'Closing', icon: <ClipboardCheck className="w-5 h-5" /> }] : []),"""
text = text.replace(old, "")
old = """      }, ... (activeBusiness?.templateType !== 'FNB' ? [{
        screen: 'CASHIER_RETURN_STOCK_MODULE' as AppScreen,
        label: 'Retur Stok',
        icon: <Package className="w-5 h-5" />,
      }] : [])] : []),"""
new = """      }, ...(isFnbCashier ? [{
        screen: 'CASHIER_CLOSING_MODULE' as AppScreen,
        label: 'Closing',
        icon: <ClipboardCheck className="w-5 h-5" />,
      }] : [{
        screen: 'CASHIER_RETURN_STOCK_MODULE' as AppScreen,
        label: 'Retur Stok',
        icon: <Package className="w-5 h-5" />,
      }])] : []),"""
if old not in text:
    raise SystemExit('FNB cashier navigation fix: Retur Stok nav block was not found')
text = text.replace(old, new)
bottom.write_text(text)
print('FNB POS stock button and Closing navigation applied')
