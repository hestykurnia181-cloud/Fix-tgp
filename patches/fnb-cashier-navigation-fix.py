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
