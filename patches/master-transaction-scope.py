from pathlib import Path
p = Path("project/src/context/TgpContext.tsx")
s = p.read_text()
old = "if (!target || !authorizedBusinesses.some((biz) => biz.businessId === target.businessId)) {"
new = "if (!target || (normalizeUserRole(actor.role) !== UserRole.MASTER && !authorizedBusinesses.some((biz) => biz.businessId === target.businessId))) {"
if new not in s:
    if old not in s:
        raise RuntimeError("transaction scope anchor missing")
    p.write_text(s.replace(old, new, 1))
print("Master transaction scope patched")
