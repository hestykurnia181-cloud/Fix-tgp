from pathlib import Path

p = Path("project/src/screens/CashierClosingScreen.tsx")
s = p.read_text(encoding="utf-8")

old_import = "import { BusinessTemplate, UserRole } from '../types';"
new_import = "import { BusinessTemplate, PaymentMethod, UserRole } from '../types';"
if old_import not in s:
    if new_import not in s:
        raise SystemExit("[closing-payment] type import anchor missing")
else:
    s = s.replace(old_import, new_import, 1)

old_context = "const {activeBusiness,activeCashierClosings,cashierClosings,activeOutlets,currentSession,activeAttendances,allUsers,createCashierClosing}=useTgp();"
new_context = "const {activeBusiness,activeCashierClosings,cashierClosings,activeOutlets,currentSession,activeAttendances,allUsers,sales,createCashierClosing}=useTgp();"
if old_context not in s:
    if new_context not in s:
        raise SystemExit("[closing-payment] context destructuring anchor missing")
else:
    s = s.replace(old_context, new_context, 1)

anchor = """ const monthRows=activeCashierClosings.filter(c=>c.dateKey.startsWith(date.slice(0,7))&&(isCashier?c.cashierUserId===currentSession?.user.userId:true));
 const monthItems=new Map<string,{name:string,qty:number}>();"""
insert = """ const monthRows=activeCashierClosings.filter(c=>c.dateKey.startsWith(date.slice(0,7))&&(isCashier?c.cashierUserId===currentSession?.user.userId:true));
 const getPaymentBreakdown=(closing:typeof activeCashierClosings[number])=>{
   const shiftSales=sales.filter(sale=>sale.businessId===closing.businessId&&sale.outletId===closing.outletId&&sale.timestamp>=closing.shiftStartedAt&&sale.timestamp<=closing.closedAt&&(sale.cashierUserId?sale.cashierUserId===closing.cashierUserId:sale.cashierName===closing.cashierName));
   const sum=(method:PaymentMethod)=>shiftSales.filter(sale=>sale.paymentMethod===method).reduce((n,sale)=>n+Number(sale.totalAmount||0),0);
   const cash=sum(PaymentMethod.CASH);
   const qris=sum(PaymentMethod.QRIS);
   const transfer=sum(PaymentMethod.TRANSFER);
   const debit=sum(PaymentMethod.DEBIT);
   const expense=Number(closing.totalExpense||0);
   return {cash,qris,transfer,debit,expense,cashNet:cash-expense};
 };
 const monthlyPayments=monthRows.reduce((totals,closing)=>{
   const b=getPaymentBreakdown(closing);
   totals.cash+=b.cash;totals.cashNet+=b.cashNet;totals.qris+=b.qris;totals.transfer+=b.transfer;totals.debit+=b.debit;totals.expense+=b.expense;
   return totals;
 },{cash:0,cashNet:0,qris:0,transfer:0,debit:0,expense:0});
 const monthItems=new Map<string,{name:string,qty:number}>();"""
if s.count(anchor) != 1:
    raise SystemExit(f"[closing-payment] month rows anchor expected 1, got {s.count(anchor)}")
s=s.replace(anchor,insert,1)

old_list = """<span className="block text-[10px] text-slate-500">{new Date(c.closedAt).toLocaleTimeString('id-ID')} · Bersih {rupiah(c.netIncome)}</span>"""
new_list = """<span className="block text-[10px] text-slate-500">{new Date(c.closedAt).toLocaleTimeString('id-ID')} · Cash bersih {rupiah(getPaymentBreakdown(c).cashNet)} · QRIS {rupiah(getPaymentBreakdown(c).qris)} · TF {rupiah(getPaymentBreakdown(c).transfer)}</span>"""
if s.count(old_list) != 1:
    raise SystemExit(f"[closing-payment] closing list summary expected 1, got {s.count(old_list)}")
s=s.replace(old_list,new_list,1)

old_grid = """<div className="grid grid-cols-2 sm:grid-cols-4 gap-2">{[['Pemasukan kotor',rupiah(selectedClosing.grossIncome)],['Pengeluaran',rupiah(selectedClosing.totalExpense)],['Pendapatan bersih',rupiah(selectedClosing.netIncome)],['Stok dikembalikan',String(selectedClosing.totalStockReturned)]].map(([k,v])=><div key={k} className="rounded-xl bg-slate-50 p-3"><p className="text-[10px] text-slate-500">{k}</p><p className="font-black text-sm">{v}</p></div>)}</div>"""
new_grid = """<div className="grid grid-cols-2 sm:grid-cols-3 gap-2">{(()=>{const b=getPaymentBreakdown(selectedClosing);return [['Cash sebelum pengeluaran',rupiah(b.cash)],['Pengeluaran (potong Cash)',rupiah(b.expense)],['Cash setelah pengeluaran',rupiah(b.cashNet)],['QRIS',rupiah(b.qris)],['Transfer bank',rupiah(b.transfer)],['Debit',rupiah(b.debit)],['Stok dikembalikan',String(selectedClosing.totalStockReturned)]].map(([k,v])=><div key={k} className="rounded-xl bg-slate-50 p-3"><p className="text-[10px] text-slate-500">{k}</p><p className="font-black text-sm">{v}</p></div>);})()}</div>"""
if s.count(old_grid) != 1:
    raise SystemExit(f"[closing-payment] detail financial grid expected 1, got {s.count(old_grid)}")
s=s.replace(old_grid,new_grid,1)

old_month = """<div className="flex justify-between pt-3"><strong className="text-sm">Pendapatan bersih bulanan</strong><strong className="text-sm text-emerald-700">{rupiah(monthRows.reduce((n,c)=>n+c.netIncome,0))}</strong></div>"""
new_month = """<div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2 border-t pt-3">{[['Cash sebelum pengeluaran',monthlyPayments.cash],['Pengeluaran (potong Cash)',monthlyPayments.expense],['Cash setelah pengeluaran',monthlyPayments.cashNet],['QRIS',monthlyPayments.qris],['Transfer bank',monthlyPayments.transfer],['Debit',monthlyPayments.debit]].map(([k,v])=><div key={k} className="rounded-xl bg-slate-50 p-3"><p className="text-[10px] text-slate-500">{k}</p><p className="text-sm font-black">{rupiah(Number(v))}</p></div>)}</div>"""
if s.count(old_month) != 1:
    raise SystemExit(f"[closing-payment] monthly net summary expected 1, got {s.count(old_month)}")
s=s.replace(old_month,new_month,1)

p.write_text(s, encoding="utf-8")
print("[closing-payment] closing history now shows cash, QRIS, transfer, debit; each shift expense is deducted from cash only.")
