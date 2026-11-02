from pathlib import Path

root = Path("project")

def replace_once(path, old, new, label):
    p = root / path
    s = p.read_text(encoding="utf-8")
    if new in s:
        return
    if old not in s:
        raise SystemExit(f"Missing {label} in {path}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# Make stock input durable before showing success or allowing the cashier to close.
replace_once(
    "src/context/TgpContext.tsx",
    "  transferStockToStan: (outletId: string, itemId: string, quantity: number, notes?: string) => boolean;",
    "  transferStockToStan: (outletId: string, itemId: string, quantity: number, notes?: string) => Promise<boolean>;",
    "transferStockToStan context type"
)
replace_once(
    "src/context/TgpContext.tsx",
    "  const transferStockToStan = (\n",
    "  const transferStockToStan = async (\n",
    "async transferStockToStan declaration"
)
old = """    // 1. Deduct from Production Stock
    const updatedTargetItem: ItemEntity = {
      ...targetItem,
      stockQuantity: Math.max(0, targetItem.stockQuantity - quantity),
      updatedAt: nowTs,
    };
    setItems((prev) =>
      prev.map((i) => (i.itemId === itemId ? updatedTargetItem : i))
    );
    supabaseSyncService.syncItem(updatedTargetItem);

    // 2. Add to STAN Outlet Stock
    let updatedOutletStock: OutletStockEntity;
    const existing = outletStocks.find((os) => os.outletId === outletId && os.itemId === itemId);
    if (existing) {
      updatedOutletStock = { ...existing, stockQuantity: existing.stockQuantity + quantity, updatedAt: nowTs };
      setOutletStocks((prev) =>
        prev.map((os) => (os.stockId === existing.stockId ? updatedOutletStock : os))
      );
    } else {
      updatedOutletStock = {
        stockId: 'ostk-' + nowTs + '-' + Math.floor(Math.random() * 1000),
        outletId,
        businessId: activeBusinessId,
        itemId: targetItem.itemId,
        itemName: targetItem.name,
        sku: targetItem.sku,
        category: targetItem.category,
        sellingPrice: targetItem.sellingPrice,
        costPrice: targetItem.costPrice,
        unit: targetItem.unit,
        stockQuantity: quantity,
        updatedAt: nowTs,
      };
      setOutletStocks((prev) => [...prev, updatedOutletStock]);
    }
    supabaseSyncService.syncOutletStock(updatedOutletStock);

    // 3. Record Stan Transfer Entry
    const transferEntry: StanTransferEntity = {
      transferId: 'strf-' + nowTs,
      transferReference: refNo,
      businessId: activeBusinessId,
      outletId,
      outletName: targetOutlet.name,
      direction: 'PRODUCTION_TO_STAN',
      itemId,
      itemName: targetItem.name,
      quantity,
      timestamp: nowTs,
      performedBy: currentSession?.user.fullName || 'Admin',
      notes: notes?.trim() || `Pasokan stok dari Gudang Produksi ke ${targetOutlet.name}`,
    };
    setStanTransfers((prev) => [transferEntry, ...prev]);
    supabaseSyncService.syncStanTransfer(transferEntry);

    addAuditLog('STAN_STOCK_SUPPLY', `Pasokan ${quantity} ${targetItem.unit} '${targetItem.name}' ke ${targetOutlet.name} (${refNo})`, activeBusinessId);
    setUserMessage(`Berhasil mengirim ${quantity} ${targetItem.unit} '${targetItem.name}' ke ${targetOutlet.name}!`);
    return true;"""
new = """    // Prepare all three records, then persist them before mutating local state.
    const updatedTargetItem: ItemEntity = {
      ...targetItem,
      stockQuantity: Math.max(0, targetItem.stockQuantity - quantity),
      updatedAt: nowTs,
    };
    const existing = outletStocks.find((os) => os.businessId === activeBusinessId && os.outletId === outletId && os.itemId === itemId);
    const updatedOutletStock: OutletStockEntity = existing
      ? { ...existing, stockQuantity: existing.stockQuantity + quantity, updatedAt: nowTs }
      : {
          stockId: 'ostk-' + nowTs + '-' + Math.floor(Math.random() * 1000),
          outletId,
          businessId: activeBusinessId,
          itemId: targetItem.itemId,
          itemName: targetItem.name,
          sku: targetItem.sku,
          category: targetItem.category,
          sellingPrice: targetItem.sellingPrice,
          costPrice: targetItem.costPrice,
          unit: targetItem.unit,
          stockQuantity: quantity,
          updatedAt: nowTs,
        };
    const transferEntry: StanTransferEntity = {
      transferId: 'strf-' + nowTs,
      transferReference: refNo,
      businessId: activeBusinessId,
      outletId,
      outletName: targetOutlet.name,
      direction: 'PRODUCTION_TO_STAN',
      itemId,
      itemName: targetItem.name,
      quantity,
      timestamp: nowTs,
      performedBy: currentSession?.user.fullName || 'Admin',
      notes: notes?.trim() || `Pasokan stok dari Gudang Produksi ke ${targetOutlet.name}`,
    };

    try {
      await Promise.all([
        supabaseSyncService.syncItem(updatedTargetItem),
        supabaseSyncService.syncOutletStock(updatedOutletStock),
        supabaseSyncService.syncStanTransfer(transferEntry),
      ]);
    } catch (error: any) {
      setErrorMessage('Input stok gagal tersimpan lengkap di server: ' + (error?.message || 'Kesalahan database') + '. Stok lokal tidak diubah; silakan coba kembali.');
      return false;
    }

    setItems((prev) => prev.map((i) => (i.itemId === itemId ? updatedTargetItem : i)));
    setOutletStocks((prev) => existing
      ? prev.map((os) => os.stockId === existing.stockId ? updatedOutletStock : os)
      : [...prev, updatedOutletStock]);
    setStanTransfers((prev) => [transferEntry, ...prev]);

    addAuditLog('STAN_STOCK_SUPPLY', `Pasokan ${quantity} ${targetItem.unit} '${targetItem.name}' ke ${targetOutlet.name} (${refNo})`, activeBusinessId);
    setUserMessage(`Berhasil mengirim ${quantity} ${targetItem.unit} '${targetItem.name}' ke ${targetOutlet.name}!`);
    return true;"""
replace_once("src/context/TgpContext.tsx", old, new, "durable stock transfer persistence")

replace_once(
    "src/screens/CashierStockInScreen.tsx",
    "const ok=transferStockToStan(outlet.outletId,entry.item.itemId,entry.qty,'Input stok oleh kasir saat mulai/selama shift.');",
    "const ok=await transferStockToStan(outlet.outletId,entry.item.itemId,entry.qty,'Input stok oleh kasir saat mulai/selama shift.');",
    "cashier stock-in awaits durable transfer"
)
replace_once(
    "src/components/Dialogs.tsx",
    "    const ok = transferStockToStan(outletId, itemId, num, notes);",
    "    const ok = await transferStockToStan(outletId, itemId, num, notes);",
    "admin stock transfer awaits durable transfer"
)
print("Stock input now awaits successful persistence of warehouse stock, STAN stock, and inbound transfer history before reporting success.")
