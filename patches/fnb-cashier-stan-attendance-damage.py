from pathlib import Path
root = Path("project")

def replace(path, old, new, count=1):
    p = root / path
    text = p.read_text(encoding="utf-8")
    found = text.count(old)
    if found < count:
        raise SystemExit(f"{path}: expected {count} match(es), found {found}: {old[:80]!r}")
    p.write_text(text.replace(old, new, count), encoding="utf-8")

# F&B cashier accounts can be created without a STAN.
replace("src/context/TgpContext.tsx",
    "if (role === UserRole.KASIR && hasStanModule && hasOutlets && !outletId) {",
    "if (role === UserRole.KASIR && targetBiz.templateType !== BusinessTemplate.FNB && hasStanModule && hasOutlets && !outletId) {")

# Do not silently attach an unassigned cashier to the first STAN; F&B can use business stock.
replace("src/context/TgpContext.tsx", """    // Self-heal a stale local account when the business has exactly one active STAN.
    // The cashier remains permanently bound to that real STAN; payment never falls back
    // to the production warehouse or an arbitrary outlet.
    if (role === UserRole.KASIR && !targetOutletId) {
      const activeBusinessOutlets = outlets.filter(
        (o) => o.businessId === effectiveBusinessId && o.status === 'ACTIVE'
      );
      if (activeBusinessOutlets.length === 1) {
        targetOutletId = activeBusinessOutlets[0].outletId;
        const repairedUser = { ...freshUser, businessId: effectiveBusinessId, outletId: targetOutletId };
        setUsers((prev) => prev.map((u) => (u.userId === repairedUser.userId ? repairedUser : u)));
        supabaseSyncService.syncUser(repairedUser);
        setCurrentSession((prev) =>
          prev && prev.user.userId === repairedUser.userId
            ? { ...prev, user: repairedUser, staffBinding: { businessId: effectiveBusinessId, role: repairedUser.role, outletId: targetOutletId } }
            : prev
        );
      }
    }

    if (role === UserRole.KASIR && !targetOutletId && businesses.find((b) => b.businessId === effectiveBusinessId)?.templateType !== BusinessTemplate.SERVICE) {
      setErrorMessage('Akun Kasir belum memiliki STAN/Outlet penugasan. Silakan minta Admin Owner menugaskan STAN/Outlet terlebih dahulu.');
      return null;
    }
""", """    // F&B cashiers may operate without a STAN and use business-level stock.
    // Never silently bind an unassigned cashier to an arbitrary outlet.
    const effectiveBusiness = businesses.find((b) => b.businessId === effectiveBusinessId);
    const cashierMayUseBusinessStock = effectiveBusiness?.templateType === BusinessTemplate.FNB || effectiveBusiness?.templateType === BusinessTemplate.SERVICE;
    if (role === UserRole.KASIR && !targetOutletId && !cashierMayUseBusinessStock) {
      setErrorMessage('Akun Kasir belum memiliki STAN/Outlet penugasan. Silakan minta Admin Owner menugaskan STAN/Outlet terlebih dahulu.');
      return null;
    }
""")
replace("src/context/TgpContext.tsx",
    "if (role === UserRole.KASIR && !targetOutlet && businesses.find((b) => b.businessId === effectiveBusinessId)?.templateType !== BusinessTemplate.SERVICE) {",
    "if (role === UserRole.KASIR && targetOutletId && !targetOutlet) {")

# Cashier identity is stored on each sale, so personal reporting does not depend on display-name uniqueness.
replace("src/types.ts",
    "  cashierName: string;\n  /** Petugas yang benar-benar melayani jasa pada transaksi SERVICE. */",
    "  cashierName: string;\n  cashierUserId?: string;\n  /** Petugas yang benar-benar melayani jasa pada transaksi SERVICE. */")
replace("src/context/TgpContext.tsx",
    "      cashierName: currentSession.user.fullName,\n      serviceStaffId: serviceStaffIdSnapshot,",
    "      cashierName: currentSession.user.fullName,\n      cashierUserId: currentSession.user.userId,\n      serviceStaffId: serviceStaffIdSnapshot,")
replace("src/services/supabaseSyncService.ts",
    "    cashierName: row.cashier_name,\n    serviceStaffId: row.service_staff_id || undefined,",
    "    cashierName: row.cashier_name,\n    cashierUserId: row.cashier_user_id || undefined,\n    serviceStaffId: row.service_staff_id || undefined,")
replace("src/services/supabaseSyncService.ts",
    "    cashier_name: entity.cashierName,\n    service_staff_id: entity.serviceStaffId || null,",
    "    cashier_name: entity.cashierName,\n    cashier_user_id: entity.cashierUserId || null,\n    service_staff_id: entity.serviceStaffId || null,")

# Cashier sales report includes all periods for the active business and filters by user ID.
replace("src/screens/ReportsScreen.tsx", "    activeSales,\n    activeBusinessFinance,", "    activeSales,\n    sales,\n    activeBusinessFinance,")
replace("src/screens/ReportsScreen.tsx",
    "  const [dateFilter, setDateFilter] = useState<'TODAY' | 'WEEK' | 'MONTH'>('TODAY');",
    "  const [dateFilter, setDateFilter] = useState<'TODAY' | 'WEEK' | 'MONTH' | 'ALL'>('TODAY');")
replace("src/screens/ReportsScreen.tsx",
    "    return activeSales.filter((sale) => !isCashier || sale.cashierName === currentSession?.user.fullName);\n  }, [activeSales, currentSession?.user.fullName, isCashier]);",
    """    const sourceSales = isCashier ? sales : activeSales;
    return sourceSales.filter((sale) => {
      if (sale.businessId !== activeBusiness?.businessId) return false;
      if (!isCashier) return true;
      return sale.cashierUserId
        ? sale.cashierUserId === currentSession?.user.userId
        : sale.cashierName === currentSession?.user.fullName;
    });
  }, [activeSales, sales, activeBusiness?.businessId, currentSession?.user.userId, currentSession?.user.fullName, isCashier]);""")
replace("src/screens/ReportsScreen.tsx",
    "      if (dateFilter === 'TODAY') return time >= todayStart.getTime();\n      if (dateFilter === 'WEEK') return time >= weekStart.getTime();\n      return time >= monthStart.getTime();",
    "      if (dateFilter === 'ALL') return true;\n      if (dateFilter === 'TODAY') return time >= todayStart.getTime();\n      if (dateFilter === 'WEEK') return time >= weekStart.getTime();\n      return time >= monthStart.getTime();")
replace("src/screens/ReportsScreen.tsx",
    "  const periodLabel = dateFilter === 'TODAY' ? 'Harian' : dateFilter === 'WEEK' ? 'Mingguan' : 'Bulanan';",
    "  const periodLabel = dateFilter === 'ALL' ? 'Semua Periode' : dateFilter === 'TODAY' ? 'Harian' : dateFilter === 'WEEK' ? 'Mingguan' : 'Bulanan';")
replace("src/screens/ReportsScreen.tsx",
    "        {(['TODAY', 'WEEK', 'MONTH'] as const).map((value) => <button key={value} onClick={() => setDateFilter(value)} className={`px-3 py-1.5 rounded-xl font-bold ${dateFilter === value ? 'bg-teal-600 text-white' : 'bg-white border border-slate-200 text-slate-600'}`}>{value === 'TODAY' ? 'Harian' : value === 'WEEK' ? 'Mingguan' : 'Bulanan'}</button>)}",
    "        {(isCashier ? ['TODAY', 'WEEK', 'MONTH', 'ALL'] as const : ['TODAY', 'WEEK', 'MONTH'] as const).map((value) => <button key={value} onClick={() => setDateFilter(value)} className={`px-3 py-1.5 rounded-xl font-bold ${dateFilter === value ? 'bg-teal-600 text-white' : 'bg-white border border-slate-200 text-slate-600'}`}>{value === 'TODAY' ? 'Harian' : value === 'WEEK' ? 'Mingguan' : value === 'MONTH' ? 'Bulanan' : 'Semua'}</button>)}")

# Damaged reports carry source STAN and photo; stock movements identify their outlet.
replace("src/types.ts",
    "  location: string;\n  itemId: string;\n  itemName: string;\n  quantity: number;\n  lossValue: number;\n  reason: string;",
    "  location: string;\n  outletId?: string | null;\n  photoDataUrl?: string;\n  itemId: string;\n  itemName: string;\n  quantity: number;\n  lossValue: number;\n  reason: string;")
replace("src/types.ts",
    "  businessId: string;\n  itemId: string;\n  itemName: string;\n  changeQty: number;",
    "  businessId: string;\n  outletId?: string | null;\n  itemId: string;\n  itemName: string;\n  changeQty: number;")
replace("src/services/supabaseSyncService.ts",
    "    businessId: row.business_id,\n    itemId: row.item_id,\n    itemName: row.item_name,\n    type: row.type,\n    changeQty: Number(row.change_qty || 0),",
    "    businessId: row.business_id,\n    outletId: row.outlet_id || null,\n    itemId: row.item_id,\n    itemName: row.item_name,\n    type: row.type,\n    changeQty: Number(row.change_qty || 0),")
replace("src/services/supabaseSyncService.ts",
    "    business_id: entity.businessId,\n    item_id: entity.itemId,\n    item_name: entity.itemName,\n    type: entity.type,\n    change_qty: entity.changeQty,",
    "    business_id: entity.businessId,\n    outlet_id: entity.outletId || null,\n    item_id: entity.itemId,\n    item_name: entity.itemName,\n    type: entity.type,\n    change_qty: entity.changeQty,")
replace("src/services/supabaseSyncService.ts",
    "    itemId: row.item_id,\n    itemName: row.item_name,\n    quantity: Number(row.quantity || 0),\n    lossValue: Number(row.loss_value || 0),\n    location: row.location,",
    "    itemId: row.item_id,\n    itemName: row.item_name,\n    quantity: Number(row.quantity || 0),\n    lossValue: Number(row.loss_value || 0),\n    location: row.location,\n    outletId: row.outlet_id || null,\n    photoDataUrl: row.photo_data_url || undefined,")
replace("src/services/supabaseSyncService.ts",
    "    location: entity.location,\n    reason: entity.reason,",
    "    location: entity.location,\n    outlet_id: entity.outletId || null,\n    photo_data_url: entity.photoDataUrl || null,\n    reason: entity.reason,")

replace("src/context/TgpContext.tsx",
    "  reportDamagedGoods: (location: string, itemId: string, qty: number, reason: string) => boolean;",
    "  reportDamagedGoods: (location: string, itemId: string, qty: number, reason: string, photoDataUrl: string) => boolean;")
replace("src/context/TgpContext.tsx", """  const reportDamagedGoods = (
    location: string,
    itemId: string,
    qty: number,
    reason: string
  ): boolean => {
    if (!activeBusinessId || qty <= 0 || !reason.trim() || !currentSession) return false;
    const role = normalizeUserRole(currentSession.user.role);
    const assignedOutlet = role === UserRole.KASIR && currentSession.user.outletId
      ? outlets.find((o) => o.outletId === currentSession.user.outletId && o.businessId === activeBusinessId && o.status === 'ACTIVE')
      : null;
    if (role === UserRole.KASIR && !assignedOutlet) {
      setErrorMessage('STAN/Outlet Kasir tidak ditemukan atau sudah dihapus.');
      return false;
    }
    const targetItem = items.find((i) => i.itemId === itemId);
    if (!targetItem) {
      setErrorMessage('Item tidak ditemukan.');
      return false;
    }

    const unitCost = targetItem.costPrice > 0 ? targetItem.costPrice : targetItem.sellingPrice;
    const lossValue = unitCost * qty;

    const newReport: DamagedGoodsReportEntity = {
      reportId: 'dmg-' + Date.now(),
      businessId: activeBusinessId,
      location: assignedOutlet?.name || location || targetItem.location,
      itemId,
      itemName: targetItem.name,
      quantity: qty,
      lossValue,
      reason: reason.trim(),
      reportedBy: currentSession?.user.fullName || 'Staff',
      status: DamagedStatus.PENDING,
      timestamp: Date.now(),
    };
""", """  const reportDamagedGoods = (
    location: string,
    itemId: string,
    qty: number,
    reason: string,
    photoDataUrl: string
  ): boolean => {
    if (!activeBusinessId || qty <= 0 || !reason.trim() || !photoDataUrl || !currentSession) return false;
    const role = normalizeUserRole(currentSession.user.role);
    const assignedOutlet = role === UserRole.KASIR && currentSession.user.outletId
      ? outlets.find((o) => o.outletId === currentSession.user.outletId && o.businessId === activeBusinessId && o.status === 'ACTIVE')
      : null;
    if (role === UserRole.KASIR && !assignedOutlet) {
      setErrorMessage('Laporan barang rusak hanya tersedia untuk Kasir yang memiliki STAN aktif.');
      return false;
    }
    const targetItem = items.find((i) => i.itemId === itemId && i.businessId === activeBusinessId);
    if (!targetItem) {
      setErrorMessage('Item tidak ditemukan pada bisnis aktif.');
      return false;
    }
    const stanStock = assignedOutlet ? outletStocks.find((s) => s.outletId === assignedOutlet.outletId && s.itemId === itemId && s.businessId === activeBusinessId) : null;
    const availableQty = assignedOutlet ? Number(stanStock?.stockQuantity || 0) : Number(targetItem.stockQuantity || 0);
    if (assignedOutlet && !stanStock) {
      setErrorMessage('Produk ini tidak tercatat pada stok STAN yang ditugaskan.');
      return false;
    }
    if (qty > availableQty) {
      setErrorMessage(`Jumlah rusak melebihi stok tersedia (${availableQty} ${targetItem.unit}) di ${assignedOutlet?.name || 'gudang bisnis'}.`);
      return false;
    }

    const unitCost = targetItem.costPrice > 0 ? targetItem.costPrice : targetItem.sellingPrice;
    const lossValue = unitCost * qty;

    const newReport: DamagedGoodsReportEntity = {
      reportId: 'dmg-' + Date.now(),
      businessId: activeBusinessId,
      location: assignedOutlet?.name || location || targetItem.location,
      outletId: assignedOutlet?.outletId || null,
      photoDataUrl,
      itemId,
      itemName: targetItem.name,
      quantity: qty,
      lossValue,
      reason: reason.trim(),
      reportedBy: currentSession?.user.fullName || 'Staff',
      status: DamagedStatus.PENDING,
      timestamp: Date.now(),
    };
""")
replace("src/context/TgpContext.tsx", """    // 1. Deduct stock safely
    const targetItem = items.find((i) => i.itemId === report.itemId);
    if (targetItem) {
      const updatedItem: ItemEntity = {
        ...targetItem,
        stockQuantity: Math.max(0, targetItem.stockQuantity - report.quantity),
        updatedAt: nowTs,
      };
      setItems((prev) =>
        prev.map((i) => (i.itemId === report.itemId ? updatedItem : i))
      );
      supabaseSyncService.syncItem(updatedItem);
    }
""", """    // 1. Deduct from the exact source stock and keep an auditable movement record.
    const targetItem = items.find((i) => i.itemId === report.itemId && i.businessId === report.businessId);
    if (!targetItem) { setErrorMessage('Item sumber laporan tidak ditemukan.'); return false; }
    let finalStock = 0;
    if (report.outletId) {
      const sourceStock = outletStocks.find((s) => s.outletId === report.outletId && s.itemId === report.itemId && s.businessId === report.businessId);
      if (!sourceStock || sourceStock.stockQuantity < report.quantity) {
        setErrorMessage('Stok STAN berubah atau tidak mencukupi. Laporan tidak dapat disetujui.');
        return false;
      }
      const updatedStock: OutletStockEntity = { ...sourceStock, stockQuantity: sourceStock.stockQuantity - report.quantity, updatedAt: nowTs };
      finalStock = updatedStock.stockQuantity;
      setOutletStocks((prev) => prev.map((s) => s.stockId === sourceStock.stockId ? updatedStock : s));
      supabaseSyncService.syncOutletStock(updatedStock);
    } else {
      if (targetItem.stockQuantity < report.quantity) {
        setErrorMessage('Stok gudang bisnis berubah atau tidak mencukupi. Laporan tidak dapat disetujui.');
        return false;
      }
      const updatedItem: ItemEntity = { ...targetItem, stockQuantity: targetItem.stockQuantity - report.quantity, updatedAt: nowTs };
      finalStock = updatedItem.stockQuantity;
      setItems((prev) => prev.map((i) => (i.itemId === report.itemId ? updatedItem : i)));
      supabaseSyncService.syncItem(updatedItem);
    }
    const stockMutation: StockMutationEntity = {
      mutationId: 'mut-dmg-' + report.reportId,
      businessId: report.businessId,
      outletId: report.outletId || null,
      itemId: report.itemId,
      itemName: report.itemName,
      changeQty: -report.quantity,
      finalQty: finalStock,
      type: MutationType.DAMAGED_GOODS,
      referenceId: report.reportId,
      note: `Write-off barang rusak (${report.location}): ${report.reason}`,
      timestamp: nowTs,
      performedBy: currentSession?.user.fullName || 'OWNER',
    };
    setStockMutations((prev) => [stockMutation, ...prev]);
    supabaseSyncService.syncStockMutation(stockMutation);
""")

# Optional STAN for F&B cashier defaults to unassigned.
replace("src/components/Dialogs.tsx",
    "import React, { useEffect, useState } from 'react';",
    "import React, { useEffect, useRef, useState } from 'react';")
replace("src/components/Dialogs.tsx", "  AlertTriangle,\n  ArrowDownToLine,", "  AlertTriangle,\n  Camera,\n  ArrowDownToLine,")
replace("src/components/Dialogs.tsx", """      const availableOutlets = outlets.filter((o) => o.businessId === initialBizId && o.status === 'ACTIVE');
      if (initialRole === UserRole.KASIR && availableOutlets.length > 0) {
        setSelectedOutletId(availableOutlets[0].outletId);
      } else {
        setSelectedOutletId('');
      }
""", """      const availableOutlets = outlets.filter((o) => o.businessId === initialBizId && o.status === 'ACTIVE');
      const initialBusiness = authorizedBusinesses.find((b) => b.businessId === initialBizId);
      if (initialRole === UserRole.KASIR && initialBusiness?.templateType !== BusinessTemplate.FNB && availableOutlets.length > 0) {
        setSelectedOutletId(availableOutlets[0].outletId);
      } else {
        setSelectedOutletId('');
      }
""")
replace("src/components/Dialogs.tsx", """    if (role === UserRole.KASIR && bizOutlets.length > 0 && !selectedOutletId) {
      setSelectedOutletId(bizOutlets[0].outletId);
    }
""", """    if (role === UserRole.KASIR && targetBiz?.templateType !== BusinessTemplate.FNB && bizOutlets.length > 0 && !selectedOutletId) {
      setSelectedOutletId(bizOutlets[0].outletId);
    }
    if (role === UserRole.KASIR && targetBiz?.templateType === BusinessTemplate.FNB) setSelectedOutletId('');
""")
replace("src/components/Dialogs.tsx", """                  const newOutlets = outlets.filter((o) => o.businessId === newBizId && o.status === 'ACTIVE');
                  setSelectedOutletId(newOutlets[0]?.outletId || '');
""", """                  const newOutlets = outlets.filter((o) => o.businessId === newBizId && o.status === 'ACTIVE');
                  const newBusiness = authorizedBusinesses.find((b) => b.businessId === newBizId);
                  setSelectedOutletId(selectedRole === UserRole.KASIR && newBusiness?.templateType === BusinessTemplate.FNB ? '' : (newOutlets[0]?.outletId || ''));
""")
replace("src/components/Dialogs.tsx", """                    Wajib Untuk Kasir
""", """                    {targetBiz?.templateType === BusinessTemplate.FNB ? 'Opsional untuk Kasir F&B' : 'Wajib Untuk Kasir'}
""")
replace("src/components/Dialogs.tsx",
    "                Tentukan gerai cabang / STAN tempat bertugasnya user ini. Transaksi POS, opname, dan laporan penjualan STAN akan terhubung langsung ke akun ini.",
    "                {targetBiz?.templateType === BusinessTemplate.FNB ? 'Pilih STAN jika kasir bertugas di gerai tertentu. Jika dikosongkan, kasir F&B akan bertransaksi menggunakan stok bisnis / gudang utama.' : 'Tentukan gerai cabang / STAN tempat bertugasnya user ini. Transaksi POS, opname, dan laporan penjualan STAN akan terhubung langsung ke akun ini.'}")

# Cashier damage report can select only stock physically assigned to their own STAN.
replace("src/components/Dialogs.tsx", """  const { activeItems, reportDamagedGoods, activeBusiness, currentSession, activeOutlets } = useTgp();
  const isCashier = currentSession?.user.role === UserRole.KASIR;
  const assignedOutlet = isCashier ? activeOutlets[0] : null;
  const [itemId, setItemId] = useState(activeItems[0]?.itemId || '');
  const [quantity, setQuantity] = useState('1');
  const [reason, setReason] = useState('Basi / Rusak Kualitas');
  const [customReason, setCustomReason] = useState('');
  const [location, setLocation] = useState('Gudang Stok');

  if (!isOpen) return null;

  const currentItem = activeItems.find((i) => i.itemId === itemId);
""", """  const { activeItems, activeOutletStocks, reportDamagedGoods, activeBusiness, currentSession, activeOutlets } = useTgp();
  const isCashier = currentSession?.user.role === UserRole.KASIR;
  const assignedOutlet = isCashier ? activeOutlets.find((o) => o.outletId === currentSession?.user.outletId) || null : null;
  const cashierStanStocks = isCashier && assignedOutlet ? activeOutletStocks.filter((s) => s.outletId === assignedOutlet.outletId && s.stockQuantity > 0) : [];
  const selectableItems = isCashier
    ? activeItems.filter((item) => cashierStanStocks.some((stock) => stock.itemId === item.itemId))
    : activeItems;
  const [itemId, setItemId] = useState(selectableItems[0]?.itemId || '');
  const [quantity, setQuantity] = useState('1');
  const [reason, setReason] = useState('Basi / Rusak Kualitas');
  const [customReason, setCustomReason] = useState('');
  const [location, setLocation] = useState('Gudang Stok');
  const [photoDataUrl, setPhotoDataUrl] = useState('');
  const photoInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const currentItem = selectableItems.find((i) => i.itemId === itemId);
  const currentStock = isCashier
    ? Number(cashierStanStocks.find((s) => s.itemId === itemId)?.stockQuantity || 0)
    : Number(currentItem?.stockQuantity || 0);
  const compressDamagePhoto = async (file: File): Promise<string> => {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, 900 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas tidak tersedia');
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    return canvas.toDataURL('image/jpeg', 0.62);
  };
  const currentStockForItem = (id: string) => Number(cashierStanStocks.find((s) => s.itemId === id)?.stockQuantity || 0);
  useEffect(() => { if (!selectableItems.some((item) => item.itemId === itemId)) setItemId(selectableItems[0]?.itemId || ''); }, [selectableItems, itemId]);
""")
replace("src/components/Dialogs.tsx",
    "    const finalLocation = isCashier ? (assignedOutlet?.name || '') : location;\n    const ok = reportDamagedGoods(finalLocation, itemId, qty, finalReason);",
    "    if (!photoDataUrl) return;\n    const finalLocation = isCashier ? (assignedOutlet?.name || '') : location;\n    const ok = reportDamagedGoods(finalLocation, itemId, qty, finalReason, photoDataUrl);")
replace("src/components/Dialogs.tsx", "      setCustomReason('');\n      onClose();", "      setCustomReason('');\n      setPhotoDataUrl('');\n      onClose();")
replace("src/components/Dialogs.tsx", """        {activeItems.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-500">
            Belum ada item di unit bisnis ini.""", """        {selectableItems.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-500">
            {isCashier ? 'Tidak ada stok tersedia di STAN yang ditugaskan.' : 'Belum ada item di unit bisnis ini.'}""")
replace("src/components/Dialogs.tsx", """                {activeItems.map((item) => (
                  <option key={item.itemId} value={item.itemId}>
                    {item.name} ({item.stockQuantity} {item.unit}) &bull; {item.location}""", """                {selectableItems.map((item) => (
                  <option key={item.itemId} value={item.itemId}>
                    {item.name} ({isCashier ? currentStockForItem(item.itemId) : item.stockQuantity} {item.unit}) &bull; {isCashier ? assignedOutlet?.name : item.location}""")
replace("src/components/Dialogs.tsx",
    "                  max={currentItem ? currentItem.stockQuantity : undefined}\n                  value={quantity}",
    "                  max={currentStock}\n                  step=\"any\"\n                  value={quantity}")
replace("src/components/Dialogs.tsx", """            {reason === 'Lainnya' && (
              <div>
                <label className="block font-bold text-slate-700 mb-1">Keterangan Tambahan</label>""", """            <div className="space-y-2">
              <label className="block font-bold text-slate-700">Foto Barang Rusak (Wajib)</label>
              <input ref={photoInputRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => { const file = e.target.files?.[0]; if (file) compressDamagePhoto(file).then(setPhotoDataUrl).catch(() => window.alert('Foto gagal diproses. Coba foto lain.')); e.currentTarget.value = ''; }} />
              <button type="button" onClick={() => photoInputRef.current?.click()} className="w-full rounded-xl border border-dashed border-rose-300 bg-rose-50 px-3 py-3 text-rose-700 font-bold flex items-center justify-center gap-2"><Camera className="w-4 h-4" />{photoDataUrl ? 'Ganti Foto' : 'Ambil / Pilih Foto'}</button>
              {photoDataUrl && <img src={photoDataUrl} alt="Bukti barang rusak" className="w-full max-h-44 object-contain rounded-xl border border-slate-200 bg-slate-50" />}
            </div>
            {reason === 'Lainnya' && (
              <div>
                <label className="block font-bold text-slate-700 mb-1">Keterangan Tambahan</label>""")
replace("src/components/Dialogs.tsx",
    "                disabled={!currentItem || currentItem.stockQuantity <= 0}\n                className=\"px-5 py-2.5 font-bold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 rounded-xl shadow-xs\"",
    "                disabled={!currentItem || currentStock <= 0 || Number(quantity) > currentStock || !photoDataUrl}\n                className=\"px-5 py-2.5 font-bold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 rounded-xl shadow-xs\"")

# Damage report list displays the attached photo.
replace("src/screens/DamagedGoodsScreen.tsx", "                <th className=\"py-2.5 px-3\">Pelapor</th>", "                <th className=\"py-2.5 px-3\">Pelapor</th>\n                <th className=\"py-2.5 px-3\">Foto</th>")
replace("src/screens/DamagedGoodsScreen.tsx", "                  <td colSpan={6} className=\"py-8 text-center text-slate-400 italic\">", "                  <td colSpan={7} className=\"py-8 text-center text-slate-400 italic\">")
replace("src/screens/DamagedGoodsScreen.tsx", """                    <td className="py-3 px-3 text-slate-600">
                      {dmg.reportedBy}
                    </td>""", """                    <td className="py-3 px-3 text-slate-600">
                      {dmg.reportedBy}
                    </td>
                    <td className="py-3 px-3">{dmg.photoDataUrl ? <a href={dmg.photoDataUrl} target="_blank" rel="noreferrer"><img src={dmg.photoDataUrl} alt="Bukti barang rusak" className="w-14 h-14 object-cover rounded-lg border" /></a> : <span className="text-slate-400">-</span>}</td>""")

# Cashier menu: attendance always; damage and stock return only for assigned STAN users.
replace("src/components/TgpBottomBar.tsx", "const { currentSession, activeBusiness, activeScreen, navigateTo, pendingTransfersForOwner, pendingDamagedForOwner, pendingStanReturnsForApproval } = useTgp();", "const { currentSession, activeBusiness, activeOutlets, activeScreen, navigateTo, pendingTransfersForOwner, pendingDamagedForOwner, pendingStanReturnsForApproval } = useTgp();")
replace("src/components/TgpBottomBar.tsx", """      {
        screen: 'DAMAGED_GOODS_MODULE',
        label: 'Barang Rusak',
        icon: <ShieldAlert className="w-5 h-5" />,
      },
      {
        screen: 'CASHIER_RETURN_STOCK_MODULE',
        label: 'Retur Stok',
        icon: <Package className="w-5 h-5" />,
      },
""", """      {
        screen: 'ATTENDANCE_MODULE',
        label: 'Absensi',
        icon: <Calendar className="w-5 h-5" />,
      },
      ...(activeOutlets.length > 0 ? [{
        screen: 'DAMAGED_GOODS_MODULE' as AppScreen,
        label: 'Barang Rusak',
        icon: <ShieldAlert className="w-5 h-5" />,
      }, {
        screen: 'CASHIER_RETURN_STOCK_MODULE' as AppScreen,
        label: 'Retur Stok',
        icon: <Package className="w-5 h-5" />,
      }] : []),
""")
replace("src/context/TgpContext.tsx", """      const allowedScreens: AppScreen[] = [
        'POS_MODULE',
        'DAMAGED_GOODS_MODULE',
        'CASHIER_RETURN_STOCK_MODULE',
        'REPORTS_MODULE',
      ];
      if (!allowedScreens.includes(screen)) {
        setErrorMessage('Akses Kasir dibatasi ke POS, laporan penjualan, Laporan Barang Rusak, dan Pengembalian Stok ke Gudang Barang Jadi.');
        return;
      }
""", """      const allowedScreens: AppScreen[] = ['POS_MODULE', 'REPORTS_MODULE', 'ATTENDANCE_MODULE'];
      if (activeOutlets.length > 0) allowedScreens.push('DAMAGED_GOODS_MODULE', 'CASHIER_RETURN_STOCK_MODULE');
      if (!allowedScreens.includes(screen)) {
        setErrorMessage('Akses Kasir dibatasi ke POS, laporan penjualan, absensi, dan fitur STAN jika memiliki penugasan STAN.');
        return;
      }
""")

# Cashier attendance requires a camera photo for both check-in and check-out, and displays only own history.
p = root / "src/screens/AttendanceScreen.tsx"
s = p.read_text(encoding="utf-8")
s = s.replace("import React, { useState } from 'react';", "import React, { useRef, useState } from 'react';")
s = s.replace("  CalendarCheck,\n  CheckCircle,", "  CalendarCheck,\n  Camera,\n  CheckCircle,")
s = s.replace("  const [note, setNote] = useState('');", """  const [note, setNote] = useState('');
  const photoInput = useRef<HTMLInputElement>(null);
  const [pendingType, setPendingType] = useState<'MASUK' | 'PULANG' | null>(null);
  const compressPhoto = async (file: File): Promise<string> => {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, 800 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas tidak tersedia');
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    return canvas.toDataURL('image/jpeg', 0.62);
  };
  const choosePhoto = (type: 'MASUK' | 'PULANG') => { setPendingType(type); photoInput.current?.click(); };
  const handlePhoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !pendingType) return;
    try {
      const photo = await compressPhoto(file);
      recordAttendance(pendingType, note || (pendingType === 'MASUK' ? 'Masuk shift kerja' : 'Selesai shift kerja'), photo);
      setNote('');
    } catch { window.alert('Foto absensi gagal diproses. Silakan coba lagi.'); }
    setPendingType(null);
    e.target.value = '';
  };
  const myAttendances = activeAttendances.filter((a) => a.userId === currentSession?.user.userId);""")
s = s.replace("""  const handleClockIn = () => {
    recordAttendance('MASUK', note || 'Masuk shift kerja');
    setNote('');
  };

  const handleClockOut = () => {
    recordAttendance('PULANG', note || 'Selesai shift kerja');
    setNote('');
  };
""", "")
s = s.replace("      {/* Clock In / Clock Out Card */}\n      <div className=\"bg-white rounded-3xl p-6", "      <input ref={photoInput} type=\"file\" accept=\"image/*\" capture=\"user\" onChange={handlePhoto} className=\"hidden\" />\n\n      {/* Clock In / Clock Out Card */}\n      <div className=\"bg-white rounded-3xl p-6")
s = s.replace("            onClick={handleClockIn}", "            onClick={() => choosePhoto('MASUK')}")
s = s.replace("            onClick={handleClockOut}", "            onClick={() => choosePhoto('PULANG')}")
s = s.replace("        <div className=\"grid grid-cols-2 gap-3 pt-2\">", "        <p className=\"text-[11px] text-slate-500 flex items-center gap-1\"><Camera className=\"w-3.5 h-3.5\" /> Foto wajib diambil saat absen masuk dan pulang.</p>\n        <div className=\"grid grid-cols-2 gap-3 pt-2\">")
s = s.replace("""          <h3 className="text-sm font-extrabold text-slate-900 tracking-wide uppercase">
            Catatan Kehadiran Divisi
          </h3>
          <span className="text-xs text-slate-400 font-semibold">
            {activeAttendances.length} Log
          </span>""", """          <h3 className="text-sm font-extrabold text-slate-900 tracking-wide uppercase">
            Riwayat Absensi Saya
          </h3>
          <span className="text-xs text-slate-400 font-semibold">
            {myAttendances.length} Log
          </span>""")
s = s.replace("{activeAttendances.length === 0 ? (", "{myAttendances.length === 0 ? (")
s = s.replace("activeAttendances.slice(0, 15).map((att) => {", "myAttendances.slice(0, 30).map((att) => {")
s = s.replace("""              const isMasuk = att.type === 'MASUK';
              return (""", """              const isMasuk = att.type === 'MASUK';
              const photoPrefix = '__TGP_ATTENDANCE_PHOTO__';
              let photo = '';
              let displayNote = att.note || '';
              if (displayNote.startsWith(photoPrefix)) { try { const parsed = JSON.parse(displayNote.slice(photoPrefix.length)); photo = typeof parsed.photo === 'string' ? parsed.photo : ''; displayNote = parsed.note || ''; } catch { displayNote = 'Absensi foto'; } }
              return (""")
s = s.replace("""                        {att.note || (isMasuk ? 'Presensi masuk kerja' : 'Presensi pulang kerja')}
                      </p>""", """                        {displayNote || (isMasuk ? 'Presensi masuk kerja' : 'Presensi pulang kerja')}
                      </p>
                      {photo && <a href={photo} target="_blank" rel="noreferrer" className="inline-block mt-2"><img src={photo} alt="Foto absensi" className="w-16 h-16 rounded-lg object-cover border" /></a>}""")
p.write_text(s, encoding="utf-8")

# Make migration available inside the extracted app source for release packaging.
migration = root / "supabase/migrations/20261030120000_fnb_cashier_stan_attendance_damage.sql"
migration.parent.mkdir(parents=True, exist_ok=True)
migration.write_text("""-- TGP F&B cashier without STAN, personal sales identity, and STAN-bound damaged-goods evidence.
-- Safe additive migration; apply in Supabase SQL Editor before deploying the updated app.
ALTER TABLE public.sales ADD COLUMN IF NOT EXISTS cashier_user_id TEXT;
ALTER TABLE public.damaged_goods ADD COLUMN IF NOT EXISTS outlet_id TEXT;
ALTER TABLE public.damaged_goods ADD COLUMN IF NOT EXISTS photo_data_url TEXT;
ALTER TABLE public.damaged_goods ADD COLUMN IF NOT EXISTS approved_by TEXT;
ALTER TABLE public.damaged_goods ADD COLUMN IF NOT EXISTS processed_at BIGINT;
ALTER TABLE public.stock_mutations ADD COLUMN IF NOT EXISTS outlet_id TEXT;
ALTER TABLE public.stock_mutations ADD COLUMN IF NOT EXISTS reference_id TEXT;
ALTER TABLE public.stock_mutations ADD COLUMN IF NOT EXISTS performed_by TEXT;

CREATE INDEX IF NOT EXISTS idx_sales_cashier_user_id ON public.sales (business_id, cashier_user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_damaged_goods_outlet_id ON public.damaged_goods (business_id, outlet_id, timestamp DESC);
""", encoding="utf-8")

# Update the reference schema for new installations.
replace("supabase-schema.sql",
    "  cashier_name TEXT NOT NULL,\n  customer_name TEXT,",
    "  cashier_name TEXT NOT NULL,\n  cashier_user_id TEXT,\n  customer_name TEXT,")
replace("supabase-schema.sql",
    "  location TEXT NOT NULL,\n  reason TEXT NOT NULL,\n  reported_by TEXT NOT NULL,",
    "  location TEXT NOT NULL,\n  outlet_id TEXT,\n  photo_data_url TEXT,\n  reason TEXT NOT NULL,\n  reported_by TEXT NOT NULL,")
replace("supabase-schema.sql",
    "  status TEXT NOT NULL,\n  reviewed_by TEXT,\n  timestamp BIGINT NOT NULL\n);",
    "  status TEXT NOT NULL,\n  reviewed_by TEXT,\n  approved_by TEXT,\n  processed_at BIGINT,\n  timestamp BIGINT NOT NULL\n);")
replace("supabase-schema.sql",
    "  business_id TEXT NOT NULL,\n  item_id TEXT NOT NULL,\n  item_name TEXT NOT NULL,\n  type TEXT NOT NULL,\n  change_qty NUMERIC NOT NULL,\n  final_qty NUMERIC NOT NULL,\n  note TEXT NOT NULL,\n  timestamp BIGINT NOT NULL",
    "  business_id TEXT NOT NULL,\n  outlet_id TEXT,\n  item_id TEXT NOT NULL,\n  item_name TEXT NOT NULL,\n  type TEXT NOT NULL,\n  change_qty NUMERIC NOT NULL,\n  final_qty NUMERIC NOT NULL,\n  reference_id TEXT,\n  note TEXT NOT NULL,\n  performed_by TEXT,\n  timestamp BIGINT NOT NULL")
print("F&B cashier and attendance patch applied.")
