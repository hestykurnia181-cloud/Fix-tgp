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
    '  decreaseStanStockToGlobal: (outletId: string, itemId: string, quantity: number) => Promise<boolean>;\n',
    'Admin Owner STAN stock reduction contract'
)

method = """  const decreaseStanStockToGlobal = async (
    outletId: string,
    itemId: string,
    requestedQuantity: number
  ): Promise<boolean> => {
    const role = currentSession ? normalizeUserRole(currentSession.user.role) : null;
    if (!currentSession || activeBusinessId !== 'biz-1790060286099' ||
        role !== UserRole.ADMIN_OWNER ||
        !(currentSession.user.assignedBusinessIds || []).includes('biz-1790060286099')) {
      setErrorMessage('Akses pengurangan stok STAN hanya tersedia untuk Admin Owner Divisi Bisnis Sekap Bungo.');
      return false;
    }
    const quantity = Number(requestedQuantity);
    if (!Number.isSafeInteger(quantity) || quantity <= 0) {
      setErrorMessage('Jumlah stok yang dikurangi harus berupa bilangan bulat lebih dari nol.');
      return false;
    }
    const outlet = outlets.find((entry) => entry.outletId === outletId &&
      entry.businessId === 'biz-1790060286099' && entry.status === 'ACTIVE');
    if (!outlet) {
      setErrorMessage('STAN tidak ditemukan atau tidak aktif.');
      return false;
    }
    const stanStock = outletStocks.find((entry) => entry.businessId === 'biz-1790060286099' &&
      entry.outletId === outletId && entry.itemId === itemId);
    if (!stanStock || stanStock.stockQuantity < quantity) {
      setErrorMessage('Stok STAN tidak mencukupi. Stok tersedia: ' + (stanStock?.stockQuantity || 0) + '.');
      return false;
    }
    const globalItem = items.find((entry) => entry.businessId === 'biz-1790060286099' &&
      entry.itemId === itemId && entry.type !== 'RAW_MATERIAL' && entry.type !== 'SERVICE');
    if (!globalItem) {
      setErrorMessage('Produk tujuan Gudang Stok Siap Jual tidak ditemukan.');
      return false;
    }
    const nowTs = Date.now();
    const updatedStanStock: OutletStockEntity = {
      ...stanStock, stockQuantity: stanStock.stockQuantity - quantity, updatedAt: nowTs,
    };
    const updatedGlobalItem: ItemEntity = {
      ...globalItem, stockQuantity: globalItem.stockQuantity + quantity, updatedAt: nowTs,
    };
    try {
      await Promise.all([
        supabaseSyncService.syncOutletStock(updatedStanStock),
        supabaseSyncService.syncItem(updatedGlobalItem),
      ]);
    } catch (error) {
      console.error('[Sekap Bungo] Admin Owner STAN stock reduction persistence failed:', error);
      setErrorMessage('Pengurangan stok gagal disimpan ke server. Stok tidak dinyatakan berhasil diubah; muat ulang dan coba lagi.');
      return false;
    }
    setOutletStocks((previous) => previous.map((entry) =>
      entry.stockId === stanStock.stockId ? updatedStanStock : entry));
    setItems((previous) => previous.map((entry) =>
      entry.itemId === globalItem.itemId ? updatedGlobalItem : entry));
    addAuditLog(
      'ADMIN_OWNER_STAN_STOCK_RETURN_TO_GLOBAL',
      'Admin Owner mengurangi ' + quantity + ' ' + globalItem.unit + ' ' + globalItem.name +
        ' dari STAN ' + outlet.name + '. Stok STAN: ' + stanStock.stockQuantity +
        ' menjadi ' + updatedStanStock.stockQuantity + '. Stok Gudang Stok Siap Jual: ' +
        globalItem.stockQuantity + ' menjadi ' + updatedGlobalItem.stockQuantity +
        '. Tidak dicatat sebagai transaksi atau laporan STAN.',
      'biz-1790060286099'
    );
    setUserMessage(quantity + ' ' + globalItem.unit + ' ' + globalItem.name +
      ' berhasil dikembalikan dari STAN ' + outlet.name + ' ke Gudang Stok Siap Jual.');
    return true;
  };

"""

replace_once(
    'src/screens/StanOutletScreen.tsx',
    "                    <button\n                      onClick={() => setSupplyOutlet(outlet)}\n                      className=\"px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-2xs transition flex items-center gap-1\"\n                    >\n                      <Send className=\"w-3 h-3\" />\n                      <span>Pasok Stok</span>\n                    </button>\n                  </div>",
    "                    <div className=\"flex items-center gap-2\">\n                      {canReduceStanStock && (\n                        <button\n                          type=\"button\"\n                          onClick={() => {\n                            setReducingOutletId(reducingOutletId === outlet.outletId ? null : outlet.outletId);\n                            setSelectedReductionStockId('');\n                            setReductionQuantity('');\n                          }}\n                          className=\"px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs rounded-xl shadow-2xs transition flex items-center gap-1\"\n                          data-testid={'btn_reduce_stan_stock_' + outlet.code}\n                        >\n                          <MinusCircle className=\"w-3 h-3\" />\n                          <span>Kurangi Stok</span>\n                        </button>\n                      )}\n                      <button\n                        onClick={() => setSupplyOutlet(outlet)}\n                        className=\"px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-2xs transition flex items-center gap-1\"\n                      >\n                        <Send className=\"w-3 h-3\" />\n                        <span>Pasok Stok</span>\n                      </button>\n                    </div>\n                  </div>\n                  {canReduceStanStock && reducingOutletId === outlet.outletId && (\n                    <div className=\"rounded-xl border border-amber-200 bg-amber-50/70 p-3 space-y-2\">\n                      <p className=\"text-xs font-bold text-amber-900\">Kurangi stok {outlet.name} dan kembalikan ke Gudang Stok Siap Jual</p>\n                      <select\n                        value={selectedReductionStockId}\n                        onChange={(event) => {\n                          setSelectedReductionStockId(event.target.value);\n                          setReductionQuantity('');\n                        }}\n                        className=\"w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-xs font-semibold text-slate-800\"\n                      >\n                        <option value=\"\">Pilih produk yang akan dikurangi</option>\n                        {outletStocks.filter((stock) => stock.stockQuantity > 0).map((stock) => (\n                          <option key={stock.stockId} value={stock.stockId}>\n                            {stock.itemName} - tersedia {stock.stockQuantity}\n                          </option>\n                        ))}\n                      </select>\n                      {(() => {\n                        const selectedStock = outletStocks.find((stock) => stock.stockId === selectedReductionStockId);\n                        if (!selectedStock) return null;\n                        return (\n                          <div className=\"flex items-center gap-2\">\n                            <input\n                              type=\"number\"\n                              min=\"1\"\n                              max={selectedStock.stockQuantity}\n                              step=\"1\"\n                              inputMode=\"numeric\"\n                              placeholder={'Jumlah (maks. ' + selectedStock.stockQuantity + ')'}\n                              value={reductionQuantity}\n                              onChange={(event) => setReductionQuantity(event.target.value)}\n                              className=\"min-w-0 flex-1 rounded-lg border border-amber-200 bg-white px-3 py-2 text-xs font-bold\"\n                            />\n                            <button\n                              type=\"button\"\n                              disabled={!Number.isSafeInteger(Number(reductionQuantity)) || Number(reductionQuantity) <= 0 || Number(reductionQuantity) > selectedStock.stockQuantity}\n                              onClick={async () => {\n                                if (await decreaseStanStockToGlobal(outlet.outletId, selectedStock.itemId, Number(reductionQuantity))) {\n                                  setReducingOutletId(null);\n                                  setSelectedReductionStockId('');\n                                  setReductionQuantity('');\n                                }\n                              }}\n                              className=\"inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-40\"\n                            >\n                              <Check className=\"h-3.5 w-3.5\" />\n                              Simpan\n                            </button>\n                            <button\n                              type=\"button\"\n                              onClick={() => {\n                                setReducingOutletId(null);\n                                setSelectedReductionStockId('');\n                                setReductionQuantity('');\n                              }}\n                              className=\"rounded-lg bg-white p-2 text-slate-500 border border-slate-200\"\n                              aria-label=\"Tutup pengurangan stok\"\n                            >\n                              <X className=\"h-4 w-4\" />\n                            </button>\n                          </div>\n                        );\n                      })()}\n                    </div>\n                  )}",
    'STAN card adjacent stock reduction control'
)




# Bind the Admin Owner-only controls inside the actual STAN screen component.
import re
p = ROOT / 'src/screens/StanOutletScreen.tsx'
s = p.read_text(encoding='utf-8')
icon_import = re.search(r"import\\s*{([^}]*)}\\s*from\\s*['\\"]lucide-react['\\"];?", s)
if not icon_import:
    raise SystemExit('lucide-react icon import not found in StanOutletScreen')
icon_names = icon_import.group(1)
for icon_name in ('MinusCircle', 'Check', 'X'):
    if icon_name not in icon_names:
        icon_names += ',\\n  ' + icon_name
s = s[:icon_import.start(1)] + icon_names + s[icon_import.end(1):]
p.write_text(s, encoding='utf-8')

replace_once(
    'src/screens/StanOutletScreen.tsx',
    '    deleteOutlet,\n',
    '    deleteOutlet,\n    currentSession,\n    decreaseStanStockToGlobal,\n',
    'STAN stock reduction context bindings'
)
replace_once(
    'src/screens/StanOutletScreen.tsx',
    "  const [selectedOutletFilter, setSelectedOutletFilter] = useState<string>('ALL');\n",
    "  const [selectedOutletFilter, setSelectedOutletFilter] = useState<string>('ALL');\n" +
    "  const [reducingOutletId, setReducingOutletId] = useState<string | null>(null);\n" +
    "  const [selectedReductionStockId, setSelectedReductionStockId] = useState('');\n" +
    "  const canReduceStanStock = activeBusiness?.businessId === 'biz-1790060286099' && currentSession?.user.role === 'ADMIN_OWNER';\n",
    'STAN stock reduction UI state'
)
