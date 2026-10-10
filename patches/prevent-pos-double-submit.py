from pathlib import Path

p = Path("project/src/context/TgpContext.tsx")
s = p.read_text()

if "const checkoutInProgressRef = useRef(false);" not in s:
    s = s.replace(
        "import React, { createContext, useContext, useEffect, useState } from 'react';",
        "import React, { createContext, useContext, useEffect, useRef, useState } from 'react';",
        1,
    )
    # Put the lock beside the checkout's state so it changes synchronously before React can re-render.
    anchor = "  const [sales, setSales] = useState<SaleOrderEntity[]>(() => loadStored('sales', INITIAL_SALES));"
    if anchor not in s:
        raise RuntimeError("sales state anchor not found; refusing to apply checkout lock")
    s = s.replace(anchor, anchor + "\n  const checkoutInProgressRef = useRef(false);", 1)

old = "  const checkoutPos = async (\n"
new = "  const checkoutPosUnlocked = async (\n"
if old in s:
    s = s.replace(old, new, 1)
elif "const checkoutPosUnlocked = async (" not in s:
    raise RuntimeError("checkoutPos function anchor not found")

wrapper = """  // Synchronous single-flight guard: rapid/double taps cannot create a second sale.
  // Keep the lock until the full sale + ledger workflow completes, including failures.
  const checkoutPos = async (...args: Parameters<typeof checkoutPosUnlocked>): Promise<SaleOrderEntity | null> => {
    if (checkoutInProgressRef.current) {
      setErrorMessage('Transaksi sedang diproses. Mohon tunggu hingga selesai.');
      return null;
    }
    checkoutInProgressRef.current = true;
    try {
      return await checkoutPosUnlocked(...args);
    } finally {
      checkoutInProgressRef.current = false;
    }
  };

"""
if "Synchronous single-flight guard: rapid/double taps cannot create a second sale." not in s:
    marker = "  // TRANSFERS (Atomic, Same Owner Only)"
    if marker not in s:
        raise RuntimeError("checkout wrapper insertion point not found")
    s = s.replace(marker, wrapper + marker, 1)

p.write_text(s)
print("Added synchronous checkout single-flight lock")
