from pathlib import Path

ROOT = Path('project')
BUSINESS_ID = 'biz-1790060286099'

def replace_once(path, old, new, label):
    p = ROOT / path
    source = p.read_text(encoding='utf-8')
    if new in source:
        return
    count = source.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected one anchor for {label}, found {count}')
    p.write_text(source.replace(old, new, 1), encoding='utf-8')

# Context contract
replace_once(
    'src/context/TgpContext.tsx',
    '  returnStockFromStan: (outletId: string, itemId: string, quantity: number, notes?: string) => boolean;\n',
    '  returnStockFromStan: (outletId: string, itemId: string, quantity: number, notes?: string) => boolean;\n'
    '  decreaseStanStockToGlobal: (outletId: string, itemId: string, quantity: number) => boolean;\n',
    'Admin Owner STAN stock reduction contract'
)

method = """  const decreaseStanStockToGlobal = (
    outletId: string,
    itemId: string,
    requestedQuantity: number
  ): boolean => {
    const role = currentSession ? normalizeUserRole(currentSession.user.role) : null;
    if (
      !currentSession ||
      activeBusinessId !== 'biz-1790060286099' ||
      role !== UserRole.ADMIN_OWNER ||
      !(currentSession.user.assignedBusinessIds || []).includes('biz-1790060286099')
    ) {
      setErrorMessage('Akses pengurangan stok STAN hanya tersedia untuk Admin Owner Divisi Bisnis Sekap Bungo.');
      return false;
    }

    const quantity = Number(requestedQuantity);
    if (!Number.isSafeInteger(quantity) || quantity <= 0) {
      setErrorMessage('Jumlah stok yang dikurangi harus berupa bilangan bulat lebih dari nol.');
      return false;
    }

    const outlet = outlets.find(
      (entry) => entry.outletId === outletId && entry.businessId === 'biz-1790060286099' && entry.status === 'ACTIVE'
    );
    if (!outlet) {
      setErrorMessage('STAN tidak ditemukan atau tidak aktif.');
      return false;
    }

    const stanStock = outletStocks.find(
      (entry) => entry.businessId === 'biz-1790060286099' && entry.outletId === outletId && entry.itemId === itemId
    );
    if (!stanStock || stanStock.stockQuantity < quantity) {
      setErrorMessage('Stok STAN tidak mencukupi. Stok tersedia: ' + (stanStock?.stockQuantity || 0) + '.');
      return false;
    }

    const globalItem = items.find(
      (entry) => entry.businessId === 'biz-1790060286099' && entry.itemId === itemId &&
        entry.type !== 'RAW_MATERIAL' && entry.type !== 'SERVICE'
    );
    if (!globalItem) {
      setErrorMessage('Produk tujuan Gudang Stok Siap Jual tidak ditemukan.');
      return false;
    }

    const nowTs = Date.now();
    const updatedStanStock: OutletStockEntity = {
      ...stanStock,
      stockQuantity: stanStock.stockQuantity - quantity,
      updatedAt: nowTs,
    };
    const updatedGlobalItem: ItemEntity = {
      ...globalItem,
      stockQuantity: globalItem.stockQuantity + quantity,
      updatedAt: nowTs,
    };

    setOutletStocks((previous) =>
      previous.map((entry) => entry.stockId === stanStock.stockId ? updatedStanStock : entry)
    );
    setItems((previous) =>
      previous.map((entry) => entry.itemId === globalItem.itemId ? updatedGlobalItem : entry)
    );
    void supabaseSyncService.syncOutletStock(updatedStanStock);
    void supabaseSyncService.syncItem(updatedGlobalItem);

    // Deliberately do not create a STAN transfer, stock mutation, ledger, sale,
    // or closing entry: this is a stock reallocation back to the central warehouse,
    // not a STAN sale/expense/report transaction.
    addAuditLog(
      'ADMIN_OWNER_STAN_STOCK_RETURN_TO_GLOBAL',
      'Admin Owner mengurangi ' + quantity + ' ' + globalItem.unit + ' ' + globalItem.name +
        ' dari STAN ' + outlet.name + '. Stok STAN: ' + stanStock.stockQuantity +
        ' menjadi ' + updatedStanStock.stockQuantity + '. Stok Gudang Stok Siap Jual: ' +
        globalItem.stockQuantity + ' menjadi ' + updatedGlobalItem.stockQuantity +
        '. Tidak dicatat sebagai transaksi atau laporan STAN.',
      'biz-1790060286099'
    );
    setUserMessage(
      quantity + ' ' + globalItem.unit + ' ' + globalItem.name +
      ' berhasil dikembalikan dari STAN ' + outlet.name + ' ke Gudang Stok Siap Jual.'
    );
    return true;
  };

"""
replace_once(
    'src/context/TgpContext.tsx',
    '  const approveStanReturn = (transferId: string): boolean => {\n',
    method + '  const approveStanReturn = (transferId: string): boolean => {\n',
    'Admin Owner STAN stock return-to-global implementation'
)
replace_once(
    'src/context/TgpContext.tsx',
    '        returnStockFromStan,\n',
    '        returnStockFromStan,\n        decreaseStanStockToGlobal,\n',
    'Admin Owner STAN stock return-to-global provider export'
)

# Show a per-item reduction control only to Admin Owner on Sekap Bungo.
replace_once(
    'src/screens/StanOutletScreen.tsx',
    '  AlertCircle,\n  ArrowRightLeft,',
    '  AlertCircle,\n  ArrowRightLeft,\n  MinusCircle,\n  Check,\n  X,',
    'STAN stock reduction icons'
)
replace_once(
    'src/screens/StanOutletScreen.tsx',
    '    deleteOutlet,\n',
    '    deleteOutlet,\n    currentSession,\n    decreaseStanStockToGlobal,\n',
    'STAN stock reduction context bindings'
)
replace_once(
    'src/screens/StanOutletScreen.tsx',
    "  const [selectedOutletFilter, setSelectedOutletFilter] = useState<string>('ALL');\n",
    "  const [selectedOutletFilter, setSelectedOutletFilter] = useState<string>('ALL');\n"
    "  const [editingStockId, setEditingStockId] = useState<string | null>(null);\n"
    "  const [reductionQuantity, setReductionQuantity] = useState('');\n"
    "  const canReduceStanStock = activeBusiness?.businessId === 'biz-1790060286099' && currentSession?.user.role === 'ADMIN_OWNER';\n",
    'STAN stock reduction UI state and access scope'
)
replace_once(
    'src/screens/StanOutletScreen.tsx',
    '                <th className="py-2.5 px-3 text-right">Nilai Barang</th>\n',
    '                <th className="py-2.5 px-3 text-right">Nilai Barang</th>\n'
    '                {canReduceStanStock && <th className="py-2.5 px-3 text-right">Aksi</th>}\n',
    'STAN stock reduction table header'
)
replace_once(
    'src/screens/StanOutletScreen.tsx',
    '                  <td colSpan={5} className="py-8 text-center text-slate-400 italic">\n',
    '                  <td colSpan={canReduceStanStock ? 6 : 5} className="py-8 text-center text-slate-400 italic">\n',
    'STAN stock reduction empty row span'
)
replace_once(
    'src/screens/StanOutletScreen.tsx',
    """                      <td className="py-3 px-3 text-right font-bold text-slate-900">
                        {formatRupiah(totalValue)}
                      </td>
                    </tr>""",
    """                      <td className="py-3 px-3 text-right font-bold text-slate-900">
                        {formatRupiah(totalValue)}
                      </td>
                      {canReduceStanStock && (
                        <td className="py-3 px-3 text-right">
                          {editingStockId === stock.stockId ? (
                            <div className="flex items-center justify-end gap-1.5">
                              <input
                                type="number"
                                min="1"
                                max={stock.stockQuantity}
                                step="1"
                                inputMode="numeric"
                                aria-label={'Jumlah pengurangan stok ' + stock.itemName + ' di ' + (outlet?.name || 'STAN')}
                                value={reductionQuantity}
                                onChange={(event) => setReductionQuantity(event.target.value)}
                                className="w-20 rounded-lg border border-amber-300 px-2 py-1.5 text-right text-sm font-bold focus:ring-2 focus:ring-amber-500"
                              />
                              <button
                                type="button"
                                title="Simpan pengurangan stok"
                                onClick={() => {
                                  const quantity = Number(reductionQuantity);
                                  if (!Number.isSafeInteger(quantity) || quantity <= 0 || quantity > stock.stockQuantity) return;
                                  if (decreaseStanStockToGlobal(stock.outletId, stock.itemId, quantity)) {
                                    setEditingStockId(null);
                                    setReductionQuantity('');
                                  }
                                }}
                                className="rounded-lg bg-emerald-50 p-1.5 text-emerald-700 hover:bg-emerald-100"
                              >
                                <Check className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                title="Batalkan pengurangan stok"
                                onClick={() => {
                                  setEditingStockId(null);
                                  setReductionQuantity('');
                                }}
                                className="rounded-lg bg-slate-100 p-1.5 text-slate-500 hover:bg-slate-200"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              disabled={stock.stockQuantity <= 0}
                              title="Kurangi stok STAN dan kembalikan ke gudang global"
                              onClick={() => {
                                setEditingStockId(stock.stockId);
                                setReductionQuantity('');
                              }}
                              className="inline-flex items-center gap-1 rounded-lg bg-amber-50 px-2.5 py-1.5 text-[11px] font-bold text-amber-800 hover:bg-amber-100 disabled:opacity-40"
                            >
                              <MinusCircle className="h-3.5 w-3.5" />
                              Kurangi
                            </button>
                          )}
                        </td>
                      )}
                    </tr>""",
    'STAN stock reduction inline action'
)

print('Added Sekap Bungo Admin Owner-only STAN stock reduction. Quantity is returned to global ready stock; no STAN transfer, mutation, ledger, sales, or closing report is created. Audit log only.')


# Card-level control: visible beside Pasok Stok on each individual STAN card.
replace_once(
    'src/screens/StanOutletScreen.tsx',
    "  const canReduceStanStock = activeBusiness?.businessId === 'biz-1790060286099' && currentSession?.user.role === 'ADMIN_OWNER';\\n",
    "  const canReduceStanStock = activeBusiness?.businessId === 'biz-1790060286099' && currentSession?.user.role === 'ADMIN_OWNER';\\n"
    "  const [reducingOutletId, setReducingOutletId] = useState<string | null>(null);\\n"
    "  const [selectedReductionStockId, setSelectedReductionStockId] = useState('');\\n",
    'STAN card reduction state'
)

replace_once(
    'src/screens/StanOutletScreen.tsx',
    """                    <button
                      onClick={() => setSupplyOutlet(outlet)}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-2xs transition flex items-center gap-1"
                    >
                      <Send className="w-3 h-3" />
                      <span>Pasok Stok</span>
                    </button>
                  </div>""",
    """                    <div className="flex items-center gap-2">
                      {canReduceStanStock && (
                        <button
                          type="button"
                          onClick={() => {
                            setReducingOutletId(reducingOutletId === outlet.outletId ? null : outlet.outletId);
                            setSelectedReductionStockId('');
                            setReductionQuantity('');
                          }}
                          className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs rounded-xl shadow-2xs transition flex items-center gap-1"
                          data-testid={'btn_reduce_stan_stock_' + outlet.code}
                        >
                          <MinusCircle className="w-3 h-3" />
                          <span>Kurangi Stok</span>
                        </button>
                      )}
                      <button
                        onClick={() => setSupplyOutlet(outlet)}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-2xs transition flex items-center gap-1"
                      >
                        <Send className="w-3 h-3" />
                        <span>Pasok Stok</span>
                      </button>
                    </div>
                  </div>
                  {canReduceStanStock && reducingOutletId === outlet.outletId && (
                    <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 space-y-2">
                      <p className="text-xs font-bold text-amber-900">Kurangi stok {outlet.name} dan kembalikan ke Gudang Stok Siap Jual</p>
                      <select
                        value={selectedReductionStockId}
                        onChange={(event) => {
                          setSelectedReductionStockId(event.target.value);
                          setReductionQuantity('');
                        }}
                        className="w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-xs font-semibold text-slate-800"
                      >
                        <option value="">Pilih produk yang akan dikurangi</option>
                        {outletStocks.filter((stock) => stock.stockQuantity > 0).map((stock) => (
                          <option key={stock.stockId} value={stock.stockId}>
                            {stock.itemName} — tersedia {stock.stockQuantity}
                          </option>
                        ))}
                      </select>
                      {(() => {
                        const selectedStock = outletStocks.find((stock) => stock.stockId === selectedReductionStockId);
                        if (!selectedStock) return null;
                        return (
                          <div className="flex items-center gap-2">
                            <input
                              type="number"
                              min="1"
                              max={selectedStock.stockQuantity}
                              step="1"
                              inputMode="numeric"
                              placeholder={'Jumlah (maks. ' + selectedStock.stockQuantity + ')'}
                              value={reductionQuantity}
                              onChange={(event) => setReductionQuantity(event.target.value)}
                              className="min-w-0 flex-1 rounded-lg border border-amber-200 bg-white px-3 py-2 text-xs font-bold"
                            />
                            <button
                              type="button"
                              disabled={!Number.isSafeInteger(Number(reductionQuantity)) || Number(reductionQuantity) <= 0 || Number(reductionQuantity) > selectedStock.stockQuantity}
                              onClick={() => {
                                if (decreaseStanStockToGlobal(outlet.outletId, selectedStock.itemId, Number(reductionQuantity))) {
                                  setReducingOutletId(null);
                                  setSelectedReductionStockId('');
                                  setReductionQuantity('');
                                }
                              }}
                              className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-40"
                            >
                              <Check className="h-3.5 w-3.5" />
                              Simpan
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setReducingOutletId(null);
                                setSelectedReductionStockId('');
                                setReductionQuantity('');
                              }}
                              className="rounded-lg bg-white p-2 text-slate-500 border border-slate-200"
                              aria-label="Tutup pengurangan stok"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        );
                      })()}
                    </div>
                  )}""",
    'STAN card adjacent stock reduction control'
)
