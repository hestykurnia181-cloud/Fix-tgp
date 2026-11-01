from pathlib import Path

path = Path("project/src/components/Dialogs.tsx")
if not path.exists():
    raise SystemExit("Damaged goods runtime guard: Dialogs.tsx missing")
source = path.read_text()

old_export = """export const ReportDamagedGoodsDialog: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {"""
new_export = """type ReportDamagedGoodsDialogProps = {
  isOpen: boolean;
  onClose: () => void;
};

const ReportDamagedGoodsDialogContent: React.FC<ReportDamagedGoodsDialogProps> = ({ isOpen, onClose }) => {"""
if old_export in source:
    source = source.replace(old_export, new_export, 1)
elif "const ReportDamagedGoodsDialogContent:" not in source:
    raise SystemExit("Damaged goods runtime guard: dialog component declaration not found")

old_state = """  const { activeItems, activeOutletStocks, reportDamagedGoods, activeBusiness, currentSession, activeOutlets } = useTgp();
  const isCashier = currentSession?.user.role === UserRole.KASIR;
  const assignedOutlet = isCashier ? activeOutlets.find((o) => o.outletId === currentSession?.user.outletId) || null : null;
  const cashierStanStocks = isCashier && assignedOutlet ? activeOutletStocks.filter((s) => s.outletId === assignedOutlet.outletId && s.stockQuantity > 0) : [];
  const selectableItems = isCashier
    ? activeItems.filter((item) => cashierStanStocks.some((stock) => stock.itemId === item.itemId))
    : activeItems;"""
new_state = """  const { activeItems, activeOutletStocks, reportDamagedGoods, activeBusiness, currentSession, activeOutlets } = useTgp();
  const safeItems = Array.isArray(activeItems) ? activeItems : [];
  const safeOutletStocks = Array.isArray(activeOutletStocks) ? activeOutletStocks : [];
  const safeOutlets = Array.isArray(activeOutlets) ? activeOutlets : [];
  const isCashier = currentSession?.user.role === UserRole.KASIR;
  const assignedOutlet = isCashier ? safeOutlets.find((o) => o.outletId === currentSession?.user.outletId) || null : null;
  const cashierStanStocks = isCashier && assignedOutlet ? safeOutletStocks.filter((s) => s.outletId === assignedOutlet.outletId && s.stockQuantity > 0) : [];
  const selectableItems = isCashier
    ? safeItems.filter((item) => cashierStanStocks.some((stock) => stock.itemId === item.itemId))
    : safeItems;"""
if old_state in source:
    source = source.replace(old_state, new_state, 1)
elif "const safeOutletStocks = Array.isArray(activeOutletStocks)" not in source:
    raise SystemExit("Damaged goods runtime guard: dialog data selector not found")

old_effect = """  // Keep hook order identical whether the dialog is open or closed.
  useEffect(() => {
    if (!selectableItems.some((item) => item.itemId === itemId)) {
      setItemId(selectableItems[0]?.itemId || '');
    }
  }, [isOpen, itemId, selectableItems]);

  if (!isOpen) return null;

  const currentItem = selectableItems.find((i) => i.itemId === itemId);
  const currentStock = isCashier
    ? Number(cashierStanStocks.find((s) => s.itemId === itemId)?.stockQuantity || 0)
    : Number(currentItem?.stockQuantity || 0);"""
new_effect = """  if (!isOpen) return null;

  // Derive a valid selection instead of synchronizing state from an effect.
  // This remains safe when a cashier has no stock or their assigned outlet changes.
  const effectiveItemId = selectableItems.some((item) => item.itemId === itemId)
    ? itemId
    : selectableItems[0]?.itemId || '';
  const currentItem = selectableItems.find((i) => i.itemId === effectiveItemId);
  const currentStock = isCashier
    ? Number(cashierStanStocks.find((s) => s.itemId === effectiveItemId)?.stockQuantity || 0)
    : Number(currentItem?.stockQuantity || 0);"""
if old_effect in source:
    source = source.replace(old_effect, new_effect, 1)
elif "const effectiveItemId = selectableItems.some" not in source:
    raise SystemExit("Damaged goods runtime guard: dialog selection/effect block not found")

source = source.replace("    if (!itemId) return;\n    const qty = parseFloat(quantity);", "    if (!effectiveItemId) return;\n    const qty = parseFloat(quantity);", 1)
source = source.replace("reportDamagedGoods(finalLocation, itemId, qty, finalReason, photoDataUrl)", "reportDamagedGoods(finalLocation, effectiveItemId, qty, finalReason, photoDataUrl)", 1)
# Only replace the select's value in the damaged-goods dialog, not unrelated dialogs.
start = source.index("const ReportDamagedGoodsDialogContent:")
end = source.index("export const AddLedgerDialog", start)
part = source[start:end]
part = part.replace("                value={itemId}\n                onChange={(e) => setItemId(e.target.value)}", "                value={effectiveItemId}\n                onChange={(e) => setItemId(e.target.value)}", 1)
source = source[:start] + part + source[end:]

# Keep the dialog isolated to its own component; avoid a class boundary that
# is incompatible with the project's React type configuration.
wrapper_start = source.find("class ReportDamagedGoodsDialogErrorBoundary")
wrapper_end = source.find("export const AddLedgerDialog", wrapper_start)
if wrapper_start >= 0 and wrapper_end >= 0:
    source = source[:wrapper_start] + "export const ReportDamagedGoodsDialog: React.FC<ReportDamagedGoodsDialogProps> = ReportDamagedGoodsDialogContent;\n\n" + source[wrapper_end:]

path.write_text(source)
print("Damaged goods dialog now uses safe stock selection and an error boundary")
