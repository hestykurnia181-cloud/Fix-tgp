from pathlib import Path

ROOT = Path('project')

def replace_once(path, old, new, label):
    p = ROOT / path
    source = p.read_text(encoding='utf-8')
    count = source.count(old)
    if new in source:
        return
    if count != 1:
        raise SystemExit(f'{path}: expected one anchor for {label}, found {count}')
    p.write_text(source.replace(old, new, 1), encoding='utf-8')

replace_once(
    'src/context/TgpContext.tsx',
    "  addItem: (itemData: Omit<ItemEntity, 'itemId' | 'businessId' | 'updatedAt'>) => boolean;\n",
    "  addItem: (itemData: Omit<ItemEntity, 'itemId' | 'businessId' | 'updatedAt'>) => boolean;\n"
    "  updateFinishedGoodsStockQuantity: (itemId: string, quantity: number) => boolean;\n",
    'inventory context contract'
)

method = """  const updateFinishedGoodsStockQuantity = (itemId: string, requestedQuantity: number): boolean => {
    const role = currentSession ? normalizeUserRole(currentSession.user.role) : null;
    if (activeBusinessId !== 'biz-1790060286099' || role !== UserRole.ADMIN_OWNER || !currentSession) {
      setErrorMessage('Akses edit stok siap jual hanya tersedia untuk Admin Owner Divisi Bisnis Sekap Bungo.');
      return false;
    }

    const quantity = Number(requestedQuantity);
    if (!Number.isSafeInteger(quantity) || quantity < 0) {
      setErrorMessage('Jumlah stok harus berupa bilangan bulat dan tidak boleh kurang dari nol.');
      return false;
    }

    const target = items.find(
      (item) => item.itemId === itemId && item.businessId === activeBusinessId &&
        item.type !== 'RAW_MATERIAL' && item.type !== 'SERVICE'
    );
    if (!target) {
      setErrorMessage('Produk pada Gudang Stok Siap Jual tidak ditemukan.');
      return false;
    }

    const previousQuantity = Number(target.stockQuantity || 0);
    if (previousQuantity === quantity) {
      setUserMessage('Stok ' + target.name + ' tetap ' + quantity + ' ' + target.unit + '.');
      return true;
    }

    const nowTs = Date.now();
    const updated: ItemEntity = { ...target, stockQuantity: quantity, updatedAt: nowTs };
    setItems((prev) => {
      const next = prev.map((item) => item.itemId === target.itemId ? updated : item);
      saveStored('items', next);
      return next;
    });

    const mutation: StockMutationEntity = {
      mutationId: 'mut-' + nowTs + '-' + Math.floor(Math.random() * 1000),
      businessId: activeBusinessId,
      itemId: target.itemId,
      itemName: target.name,
      type: MutationType.ADJUSTMENT,
      changeQty: quantity - previousQuantity,
      finalQty: quantity,
      referenceId: 'manual-adjust-' + target.itemId + '-' + nowTs,
      note: 'Penyesuaian manual stok Gudang Stok Siap Jual: ' + previousQuantity + ' menjadi ' + quantity + ' ' + target.unit,
      timestamp: nowTs,
      performedBy: currentSession.user.fullName || currentSession.user.username || 'Admin Owner',
    };
    setStockMutations((prev) => [mutation, ...prev]);
    void supabaseSyncService.syncItem(updated);
    void supabaseSyncService.syncStockMutation(mutation);
    addAuditLog(
      'FINISHED_GOODS_STOCK_ADJUSTED',
      'Admin Owner mengubah stok siap jual ' + target.name + ' dari ' + previousQuantity + ' menjadi ' + quantity + ' ' + target.unit + '.',
      activeBusinessId
    );
    setUserMessage('Stok ' + target.name + ' berhasil diperbarui menjadi ' + quantity + ' ' + target.unit + '.');
    return true;
  };

"""
replace_once(
    'src/context/TgpContext.tsx',
    '  const produceFinishedGoods = (\n',
    method + '  const produceFinishedGoods = (\n',
    'Admin Owner finished goods stock adjustment implementation'
)
replace_once(
    'src/context/TgpContext.tsx',
    '        addItem,\n        produceFinishedGoods,',
    '        addItem,\n        updateFinishedGoodsStockQuantity,\n        produceFinishedGoods,',
    'inventory context provider export'
)

replace_once(
    'src/screens/InventoryScreen.tsx',
    "  Plus,\n  Search,",
    "  Plus,\n  Pencil,\n  Check,\n  X,\n  Search,",
    'inventory edit icons'
)
replace_once(
    'src/screens/InventoryScreen.tsx',
    '    deleteItem,\n    canAccessCostPrice,',
    '    deleteItem,\n    updateFinishedGoodsStockQuantity,\n    canAccessCostPrice,',
    'inventory stock updater binding'
)
replace_once(
    'src/screens/InventoryScreen.tsx',
    "  const [itemToDelete, setItemToDelete] = useState<ItemEntity | null>(null);\n",
    "  const [itemToDelete, setItemToDelete] = useState<ItemEntity | null>(null);\n"
    "  const [editingStockItemId, setEditingStockItemId] = useState<string | null>(null);\n"
    "  const [stockQuantityDraft, setStockQuantityDraft] = useState('');\n",
    'inventory stock edit state'
)
replace_once(
    'src/screens/InventoryScreen.tsx',
    "  const isOwner = currentSession?.user.role === UserRole.OWNER;\n",
    "  const canEditReadyStock = activeBusiness?.businessId === 'biz-1790060286099' && currentSession?.user.role === UserRole.ADMIN_OWNER;\n"
    "  const isOwner = currentSession?.user.role === UserRole.OWNER;\n",
    'Sekap Bungo Admin Owner edit scope'
)
replace_once(
    'src/screens/InventoryScreen.tsx',
    """                      <td className="py-3 px-3 text-right">
                        <span
                          className={`font-black text-sm ${
                            item.type !== 'SERVICE' && item.stockQuantity <= 5
                              ? 'text-rose-600'
                              : 'text-slate-900'
                          }`}
                        >
                          {item.type === 'SERVICE' ? 'Layanan' : `${item.stockQuantity} ${item.unit}`}
                        </span>
                      </td>""",
    """                      <td className="py-3 px-3 text-right">
                        {editingStockItemId === item.itemId && canEditReadyStock && !isRaw && item.type !== 'SERVICE' ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <input
                              type="number"
                              min="0"
                              step="1"
                              inputMode="numeric"
                              aria-label={`Jumlah stok ${item.name}`}
                              value={stockQuantityDraft}
                              onChange={(e) => setStockQuantityDraft(e.target.value)}
                              className="w-20 rounded-lg border border-blue-300 px-2 py-1.5 text-right text-sm font-bold focus:ring-2 focus:ring-blue-500"
                            />
                            <button
                              type="button"
                              title="Simpan jumlah stok"
                              onClick={() => {
                                const quantity = Number(stockQuantityDraft);
                                if (!Number.isSafeInteger(quantity) || quantity < 0) return;
                                if (updateFinishedGoodsStockQuantity(item.itemId, quantity)) {
                                  setEditingStockItemId(null);
                                  setStockQuantityDraft('');
                                }
                              }}
                              className="rounded-lg bg-emerald-50 p-1.5 text-emerald-700 hover:bg-emerald-100"
                            >
                              <Check className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              title="Batalkan edit stok"
                              onClick={() => {
                                setEditingStockItemId(null);
                                setStockQuantityDraft('');
                              }}
                              className="rounded-lg bg-slate-100 p-1.5 text-slate-500 hover:bg-slate-200"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center justify-end gap-2">
                            <span
                              className={`font-black text-sm ${
                                item.type !== 'SERVICE' && item.stockQuantity <= 5
                                  ? 'text-rose-600'
                                  : 'text-slate-900'
                              }`}
                            >
                              {item.type === 'SERVICE' ? 'Layanan' : `${item.stockQuantity} ${item.unit}`}
                            </span>
                            {canEditReadyStock && !isRaw && item.type !== 'SERVICE' && (
                              <button
                                type="button"
                                title="Edit jumlah stok siap jual"
                                onClick={() => {
                                  setEditingStockItemId(item.itemId);
                                  setStockQuantityDraft(String(item.stockQuantity));
                                }}
                                className="rounded-lg bg-blue-50 p-1.5 text-blue-700 hover:bg-blue-100"
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </button>
                            )}
                          </div>
                        )}
                      </td>""",
    'ready stock quantity inline editor'
)

print('Sekap Bungo Admin Owner can edit only finished-goods warehouse quantities; each change syncs item stock, stock mutation history, and audit log. Other businesses and roles are unchanged.')
