from pathlib import Path
import re
def show(path,pats,r=5):
 lines=Path('project',path).read_text(encoding='utf-8').splitlines()
 for pat in pats:
  for i,x in enumerate(lines):
   if re.search(pat,x,re.I):
    print(f'\\n### {path}:{i+1} {pat}')
    for j in range(max(0,i-r),min(len(lines),i+r+1)): print(f'{j+1}: {lines[j]}')
show('src/components/TgpBottomBar.tsx',[r'INVENTORY',r'Inventory',r'Gudang',r'OWNER',r'ADMIN_OWNER'],6)
show('src/App.tsx',[r'INVENTORY',r'InventoryScreen',r'allowedScreens',r'case .*INVENTORY'],8)
show('src/types.ts',[r'enum MutationType',r'interface StockMutationEntity'],16)
