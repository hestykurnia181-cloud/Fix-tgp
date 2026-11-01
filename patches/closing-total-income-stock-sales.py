from pathlib import Path

p = Path("project/src/screens/CashierClosingScreen.tsx")
s = p.read_text(encoding="utf-8")

replacements = [
    (
        "   return {cash,qris,transfer,debit,expense,cashNet:cash-expense};",
        "   const totalIncome=cash+qris+transfer;\n   const stockIn=(closing.items||[]).reduce((n,item)=>n+Number(item.stockIn||0),0);\n   return {cash,qris,transfer,debit,expense,cashNet:cash-expense,totalIncome,stockIn};"
    ),
    (
        "   totals.cash+=b.cash;totals.cashNet+=b.cashNet;totals.qris+=b.qris;totals.transfer+=b.transfer;totals.debit+=b.debit;totals.expense+=b.expense;",
        "   totals.cash+=b.cash;totals.cashNet+=b.cashNet;totals.qris+=b.qris;totals.transfer+=b.transfer;totals.debit+=b.debit;totals.expense+=b.expense;totals.stockIn+=b.stockIn;totals.totalIncome+=b.totalIncome;"
    ),
    (
        " },{cash:0,cashNet:0,qris:0,transfer:0,debit:0,expense:0});",
        " },{cash:0,cashNet:0,qris:0,transfer:0,debit:0,expense:0,stockIn:0,totalIncome:0});"
    ),
    (
        "· Total pendapatan {rupiah(getPaymentBreakdown(c).cash)} · QRIS {rupiah(getPaymentBreakdown(c).qris)} · Transfer {rupiah(getPaymentBreakdown(c).transfer)} · Debit {rupiah(getPaymentBreakdown(c).debit)}",
        "· Total pendapatan {rupiah(getPaymentBreakdown(c).totalIncome)} · Cash {rupiah(getPaymentBreakdown(c).cash)} · QRIS {rupiah(getPaymentBreakdown(c).qris)} · Transfer {rupiah(getPaymentBreakdown(c).transfer)} · Stok Penjualan {getPaymentBreakdown(c).stockIn}"
    ),
    (
        "return [['Total pendapatan',rupiah(b.cash)],['Pengeluaran (mengurangi Cash)',rupiah(b.expense)],['Sisa Cash',rupiah(b.cashNet)],['QRIS',rupiah(b.qris)],['Transfer bank',rupiah(b.transfer)],['Debit',rupiah(b.debit)],['Stok dikembalikan',String(selectedClosing.totalStockReturned)]]",
        "return [['Total pendapatan',rupiah(b.totalIncome)],['Cash',rupiah(b.cash)],['QRIS',rupiah(b.qris)],['Transfer',rupiah(b.transfer)],['Stok Penjualan',String(b.stockIn)],['Pengeluaran (mengurangi Cash)',rupiah(b.expense)],['Sisa Cash',rupiah(b.cashNet)],['Stok dikembalikan',String(selectedClosing.totalStockReturned)]]"
    ),
    (
        "[['Total pendapatan',monthlyPayments.cash],['Pengeluaran (mengurangi Cash)',monthlyPayments.expense],['Sisa Cash',monthlyPayments.cashNet],['QRIS',monthlyPayments.qris],['Transfer bank',monthlyPayments.transfer],['Debit',monthlyPayments.debit]]",
        "[['Total pendapatan',monthlyPayments.totalIncome],['Cash',monthlyPayments.cash],['QRIS',monthlyPayments.qris],['Transfer',monthlyPayments.transfer],['Stok Penjualan',monthlyPayments.stockIn],['Pengeluaran (mengurangi Cash)',monthlyPayments.expense],['Sisa Cash',monthlyPayments.cashNet]]"
    ),
]

for old, new in replacements:
    if new not in s:
        if old not in s:
            raise SystemExit(f"Required closing UI anchor not found: {old[:100]}")
        s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("Closing history now totals Cash + QRIS + Transfer; Debit card removed and replaced by Stok Penjualan (sum of stockIn).")
