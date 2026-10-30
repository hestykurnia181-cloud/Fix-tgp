from pathlib import Path
root=Path('project')
def rep(path,old,new):
 p=root/path;s=p.read_text(encoding='utf-8');n=s.count(old)
 if n!=1: raise SystemExit(f'{path}: expected one match, got {n}: {old[:100]!r}')
 p.write_text(s.replace(old,new),encoding='utf-8')
rep('src/types.ts',"  | 'CASHIER_RETURN_STOCK_MODULE'\n","  | 'CASHIER_RETURN_STOCK_MODULE'\n  | 'CASHIER_EXPENSE_MODULE'\n")
rep('src/App.tsx',"import { CashierReturnStockScreen } from './screens/CashierReturnStockScreen';","import { CashierReturnStockScreen } from './screens/CashierReturnStockScreen';\nimport { CashierExpenseScreen } from './screens/CashierExpenseScreen';")
rep('src/App.tsx',"      case 'CASHIER_RETURN_STOCK_MODULE':\n        return <CashierReturnStockScreen />;","      case 'CASHIER_RETURN_STOCK_MODULE':\n        return <CashierReturnStockScreen />;\n      case 'CASHIER_EXPENSE_MODULE':\n        return <CashierExpenseScreen />;")
rep('src/components/TgpBottomBar.tsx',"""      ...(activeOutlets.some((outlet) => outlet.outletId === currentSession?.user.outletId && outlet.status === 'ACTIVE') ? [{
        screen: 'DAMAGED_GOODS_MODULE' as AppScreen,""","""      ...(activeOutlets.some((outlet) => outlet.outletId === currentSession?.user.outletId && outlet.status === 'ACTIVE') ? [{
        screen: 'CASHIER_EXPENSE_MODULE' as AppScreen,
        label: 'Pengeluaran',
        icon: <Coins className="w-5 h-5" />,
      }, {
        screen: 'DAMAGED_GOODS_MODULE' as AppScreen,""")
rep('src/context/TgpContext.tsx',"      if (activeOutlets.some((outlet) => outlet.outletId === currentSession.user.outletId && outlet.status === 'ACTIVE')) allowedScreens.push('DAMAGED_GOODS_MODULE', 'CASHIER_RETURN_STOCK_MODULE');","      if (activeOutlets.some((outlet) => outlet.outletId === currentSession.user.outletId && outlet.status === 'ACTIVE')) allowedScreens.push('DAMAGED_GOODS_MODULE', 'CASHIER_RETURN_STOCK_MODULE', 'CASHIER_EXPENSE_MODULE');")
rep('src/context/TgpContext.tsx',"      setErrorMessage('Akses Kasir dibatasi ke POS, laporan penjualan, absensi, dan fitur STAN jika memiliki penugasan STAN.');","      setErrorMessage('Akses Kasir dibatasi ke POS, laporan penjualan, absensi, serta pengeluaran dan fitur STAN pada STAN penugasannya.');")
rep('src/context/TgpContext.tsx',"""    if (!activeBusinessId || amount <= 0 || !description.trim()) {
      setErrorMessage('Nominal dan keterangan transaksi wajib diisi.');
      return false;
    }

    const nowTs = Date.now();""","""    const role = currentSession ? normalizeUserRole(currentSession.user.role) : null;
    const isCashier = role === UserRole.KASIR;
    const assignedOutlet = isCashier
      ? activeOutlets.find((outlet) => outlet.outletId === currentSession?.user.outletId && outlet.businessId === activeBusinessId && outlet.status === 'ACTIVE')
      : null;
    if (!activeBusinessId || !currentSession || !Number.isFinite(amount) || amount <= 0 || !description.trim()) {
      setErrorMessage('Nominal dan keterangan transaksi wajib diisi.'); return false;
    }
    if (isCashier && (type !== LedgerType.PENGELUARAN || !assignedOutlet)) {
      setErrorMessage('Kasir hanya dapat mencatat pengeluaran pada STAN aktif yang ditugaskan.'); return false;
    }
    if (!isCashier && ![UserRole.OWNER, UserRole.ADMIN_OWNER].includes(role as UserRole)) {
      setErrorMessage('Akses pencatatan kas ditolak.'); return false;
    }

    const nowTs = Date.now();""")
rep('src/context/TgpContext.tsx',"""      businessId: activeBusinessId,
      type,
      category: category.trim() || (type === LedgerType.PEMASUKAN ? 'Pemasukan Lain' : 'Operasional'),""","""      businessId: activeBusinessId,
      outletId: assignedOutlet?.outletId || null,
      outletName: assignedOutlet?.name || null,
      type,
      category: category.trim() || (type === LedgerType.PEMASUKAN ? 'Pemasukan Lain' : 'Operasional'),""")
rep('src/context/TgpContext.tsx',"      createdBy: currentSession?.user.username || 'staff',","      createdBy: currentSession.user.fullName || currentSession.user.username || 'staff',")

(root/'src/screens/CashierExpenseScreen.tsx').write_text("import React, { useMemo, useState } from 'react';\nimport { CalendarDays, CheckCircle2, Receipt, Wallet } from 'lucide-react';\nimport { useTgp } from '../context/TgpContext';\nimport { LedgerType, UserRole } from '../types';\nconst CATEGORIES=['Bahan baku','Es & air','Gas / listrik','Transportasi','Perlengkapan','Kebersihan','Perbaikan','Lain-lain'];\nconst rupiah=(v:number)=>'Rp '+Math.round(v).toLocaleString('id-ID');\nexport const CashierExpenseScreen:React.FC=()=>{\n const {currentSession,activeBusiness,activeOutlets,periodLedgers,addManualLedgerEntry}=useTgp();\n const [amount,setAmount]=useState(''); const [category,setCategory]=useState(CATEGORIES[0]); const [description,setDescription]=useState('');\n const outlet=activeOutlets.find(o=>o.outletId===currentSession?.user.outletId&&o.status==='ACTIVE');\n const rows=useMemo(()=>periodLedgers.filter(l=>l.type===LedgerType.PENGELUARAN&&l.outletId===outlet?.outletId).sort((a,b)=>b.timestamp-a.timestamp),[periodLedgers,outlet?.outletId]);\n const total=rows.reduce((s,r)=>s+r.amount,0);\n const submit=(e:React.FormEvent)=>{e.preventDefault();const n=Number(amount);if(!Number.isFinite(n)||n<=0||!description.trim()||!outlet)return;const ok=addManualLedgerEntry(LedgerType.PENGELUARAN,category,n,description.trim());if(ok){setAmount('');setDescription('');}};\n if(currentSession?.user.role!==UserRole.KASIR||!outlet)return <div className=\"rounded-3xl bg-white p-8 text-center text-sm font-bold text-rose-600\">Menu ini hanya tersedia untuk Kasir dengan STAN aktif.</div>;\n return <div className=\"mx-auto max-w-3xl space-y-5 pb-8\">\n <header className=\"rounded-3xl border border-slate-200 bg-white p-5 shadow-sm\"><div className=\"flex items-center gap-3\"><div className=\"flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-100 text-rose-600\"><Wallet className=\"h-6 w-6\"/></div><div><p className=\"text-xs font-bold uppercase tracking-wider text-rose-600\">Kas operasional STAN</p><h2 className=\"text-xl font-extrabold\">Pengeluaran</h2><p className=\"text-xs text-slate-500\">{activeBusiness?.name} · {outlet.name}</p></div></div><div className=\"mt-4 rounded-2xl bg-rose-50 p-4\"><p className=\"text-xs font-bold text-rose-600\">Total pengeluaran periode aktif</p><p className=\"mt-1 text-2xl font-black text-rose-700\">{rupiah(total)}</p></div></header>\n <form onSubmit={submit} className=\"space-y-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm\"><h3 className=\"flex items-center gap-2 font-extrabold\"><Receipt className=\"h-5 w-5 text-rose-600\"/>Catat pengeluaran baru</h3>\n <label className=\"block text-xs font-bold text-slate-600\">Nominal (Rp)<input required type=\"number\" min=\"1\" step=\"1\" inputMode=\"numeric\" value={amount} onChange={e=>setAmount(e.target.value)} placeholder=\"Contoh: 25000\" className=\"mt-1.5 w-full rounded-xl border border-slate-200 px-4 py-3 text-base font-bold\"/></label>\n <label className=\"block text-xs font-bold text-slate-600\">Kategori<select value={category} onChange={e=>setCategory(e.target.value)} className=\"mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm\">{CATEGORIES.map(c=><option key={c}>{c}</option>)}</select></label>\n <label className=\"block text-xs font-bold text-slate-600\">Keterangan<textarea required value={description} onChange={e=>setDescription(e.target.value)} rows={3} maxLength={300} placeholder=\"Contoh: membeli es batu dan gula untuk operasional\" className=\"mt-1.5 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm\"/></label>\n <div className=\"rounded-xl bg-slate-50 p-3 text-xs text-slate-600\"><p className=\"font-bold\">Dicatat oleh: {currentSession.user.fullName}</p><p>STAN: {outlet.name}</p></div>\n <button disabled={!amount||!description.trim()} className=\"flex w-full items-center justify-center gap-2 rounded-xl bg-rose-600 px-4 py-3 font-bold text-white disabled:opacity-50\"><CheckCircle2 className=\"h-4 w-4\"/>Simpan Pengeluaran</button></form>\n <section className=\"rounded-3xl border border-slate-200 bg-white p-5 shadow-sm\"><h3 className=\"mb-4 flex items-center gap-2 font-extrabold\"><CalendarDays className=\"h-5 w-5 text-slate-500\"/>Riwayat pengeluaran STAN</h3>{rows.length===0?<p className=\"py-8 text-center text-sm text-slate-400\">Belum ada pengeluaran pada periode aktif.</p>:<div className=\"divide-y divide-slate-100\">{rows.map(r=><div key={r.transactionId} className=\"flex items-start justify-between gap-3 py-3\"><div className=\"min-w-0\"><p className=\"font-bold text-slate-800\">{r.category}</p><p className=\"break-words text-xs text-slate-500\">{r.description}</p><p className=\"mt-1 text-[11px] text-slate-400\">{new Date(r.timestamp).toLocaleString('id-ID')} · {r.createdBy}</p></div><p className=\"shrink-0 font-extrabold text-rose-600\">-{rupiah(r.amount)}</p></div>)}</div>}</section></div>;\n};\n",encoding='utf-8')
